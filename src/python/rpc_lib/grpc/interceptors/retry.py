import grpc
import time
from rpc_lib.common import servicer
from rpc_lib.common.prometheus_metrics import CLIENT_LATENCY, CLIENT_RETRIES


def linear_backoff(start=0.01, step=0.01):
    def generator(retry_num):
        return start + retry_num * step

    return generator

class RetryCoordinator():
    max_retries_by_code = {
        grpc.StatusCode.INTERNAL: 1,
        grpc.StatusCode.ABORTED: 3,
        grpc.StatusCode.UNAVAILABLE: 3,
    }

    backoff_policy = staticmethod(linear_backoff())



class RetryInterceptor(grpc.UnaryUnaryClientInterceptor):
    def __init__(self, remote_service_name):
        super(RetryInterceptor, self).__init__()
        self._remote_service_name = remote_service_name

    def intercept_unary_unary(self, continuation, call_details, request):
        start_time = time.time()
        response, exception, retries = self._intercept_unary_unary(continuation, call_details, request)
        elapsed = time.time() - start_time

        CLIENT_RETRIES.labels(
            servicer.name(),
            self._remote_service_name,
            call_details.method,
            self._get_response_conde(exception)
        ).observe(retries)

        CLIENT_LATENCY.labels(
            servicer.name(),
            self._remote_service_name,
            call_details.method,
        ).observe(elapsed)

        if response is not None:
            return response

        raise exception

    @staticmethod
    def _get_response_conde(exception):
        if exception is None:
            return "OK"
        if not issubclass(type(exception), grpc.Call):
            return "INTERNAL"
        return exception.code() or "UNKNOWN"

    def _intercept_unary_unary(self, continuation, call_details, request):
        retries = 0
        while True:
            try:
                response = continuation(call_details, request)
                exception = response.exception()
            except Exception as e:
                exception = e
                response = None

            if exception is None:
                return response, exception, retries
            if not issubclass(type(exception), grpc.Call):
                return response, exception, retries

            code = exception.code()

            max_retries = RetryCoordinator.max_retries_by_code.get(code)
            if max_retries is None:
                return response, exception, retries

            if retries > max_retries:
                return response, exception, retries

            time.sleep(RetryCoordinator.backoff_policy(retries))

            retries += 1
