import asyncio, asyncio.futures
import concurrent.futures
import functools
import grpc
import time

from rpc_lib.grpc.interceptors.utils import RequestWithContext
from rpc_lib.grpc.interceptors import flags, retry, timeout
from rpc_lib.common import servicer
from rpc_lib.common.prometheus_metrics import CLIENT_LATENCY, CLIENT_RETRIES
from rpc_lib.grpc.grpc_client import GrpcClient

class SanicGrpcClientFactory(object):
    sanic_app = None

    def create_grpc_client(server_address):
        return SanicGrpcClient(server_address)

class SanicGrpcClient(GrpcClient):
    def __init__(self, server_address):
        super(SanicGrpcClient, self).__init__(server_address)

    def get_stub(self, stub_factory, remote_service_name, instance_name, methods=()):
        channel = grpc.intercept_channel(
                self._channel,
                flags.flags_interceptor(),
                timeout.TimeoutInterceptor(remote_service_name, instance_name))
        return create_sanic_grpc_stub(stub_factory(channel), methods, remote_service_name)

def get_response_conde(exception):
    if exception is None:
        return "OK"
    if not issubclass(type(exception), grpc.Call):
        return "INTERNAL"
    return exception.code() or "UNKNOWN"

class GrpcMethodCaller(object):
    def __init__(self, method, request, remote_service_name,  **kwargs):
        self.method = method
        self.request=RequestWithContext(request)
        self.remote_service_name = remote_service_name
        self.kwargs = kwargs
        self.result = concurrent.futures.Future()
        self.start_time = time.time()
        self.sanic_loop = SanicGrpcClientFactory.sanic_app.loop
        self.call_method(0)
 
    def set_result(self, retry_cnt, f, exception=None):
        exception = exception or f.exception()
        success = exception is None
        do_retry = False
        if success:
            self.result.set_result(f.result())
        else:
            if issubclass(type(exception), grpc.Call):
                do_retry = retry_cnt < (retry.RetryCoordinator.max_retries_by_code.get(exception.code()) or 0)
            if do_retry:
                asyncio.ensure_future(self.timeout_retry(retry_cnt), loop=self.sanic_loop)
            else:
                self.result.set_exception(exception)
        if not do_retry:
            CLIENT_RETRIES.labels(
                servicer.name(),
                self.remote_service_name,
                self.method._method,
                get_response_conde(exception)
            ).observe(retry_cnt)

            elapsed = time.time() - self.start_time
            CLIENT_LATENCY.labels(
                servicer.name(),
                self.remote_service_name,
                self.method._method,
            ).observe(elapsed)

    def call_method(self, retry_cnt):
        try:
            self.method.future(self.request, **self.kwargs).add_done_callback(functools.partial(self.set_result, retry_cnt))
        except Exception as e:
            self.set_result(retry_cnt, None, e)

    async def timeout_retry(self, retry_cnt):
        await asyncio.sleep(retry.RetryCoordinator.backoff_policy(retry_cnt))
        self.call_method(retry_cnt)

    def future(self):
       return asyncio.futures.wrap_future(self.result, loop=self.sanic_loop)

def create_sanic_grpc_stub(stub, methods, remote_service_name):
    result = lambda: None
    for method_name in methods:
        method = getattr(stub, method_name)
        f = lambda request, **kwargs: GrpcMethodCaller(method, request, remote_service_name, **kwargs).future()
        setattr(result, method_name, f)
    return result
