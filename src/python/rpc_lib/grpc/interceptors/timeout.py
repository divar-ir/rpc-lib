import logging
import grpc
import time

from rpc_lib.common import servicer
from rpc_lib.common.prometheus_metrics import CLIENT_ATTEMPT_LATENCY, CLIENT_IN_PROGRESS_REQUESTS, CLIENT_ATTEMPT_DEADLINE
from rpc_lib.third_party import client_call_details
from rpc_lib.grpc.interceptors import failure
from rpc_lib.grpc.interceptors.utils import extract_request_and_context


class TimeoutInterceptor(grpc.UnaryUnaryClientInterceptor):
    def __init__(self, remote_service_name, remote_instance_name):
        super(TimeoutInterceptor, self).__init__()
        self._remote_service_name = remote_service_name
        self._remote_instance_name = remote_instance_name

    @staticmethod
    def _get_timeout(task_context, max_timeout):
        if task_context is None:
            return max_timeout
        time_remaining = task_context.time_remaining()
        if time_remaining is None or time_remaining > 1E6:
            return max_timeout
        if max_timeout is None:
            return time_remaining
        return max_timeout if time_remaining > max_timeout else time_remaining

    @staticmethod
    def _get_response_conde(exception):
        if exception is None:
            return "OK"
        if not issubclass(type(exception), grpc.Call):
            return "INTERNAL"
        return exception.code() or "UNKNOWN"

    def intercept_unary_stream(self, continuation, client_call_details, request):
        request, _ = extract_request_and_context(request)
        return continuation(client_call_details, request)

    def intercept_unary_unary(self, continuation, call_details, request):
        request, task_context = extract_request_and_context(request)

        timeout = self._get_timeout(task_context, call_details.timeout)
        if timeout is not None and timeout <= 0:
            return failure.FailureOutcome(
                    grpc.StatusCode.DEADLINE_EXCEEDED,
                    "Skipped GRPC call since no time is remaining")

        new_details = client_call_details.create(
                call_details.method, timeout, call_details.metadata,
                call_details.credentials,
                True) # wait_for_ready

        start_time = time.time()

        def before_request():
            CLIENT_IN_PROGRESS_REQUESTS.labels(
                servicer.name(),
                self._remote_service_name,
                call_details.method
            ).inc()

            CLIENT_ATTEMPT_DEADLINE.labels(
                    servicer.name(), 
                    self._remote_service_name,
                    self._remote_instance_name,
                    call_details.method, 
                    ).observe(timeout or 1000)

        def process_response(response, exception=None):
            exception = exception or response.exception()
            elapsed = time.time() - start_time
            CLIENT_ATTEMPT_LATENCY.labels(
                    servicer.name(), 
                    self._remote_service_name, self._remote_instance_name,
                    call_details.method, 
                    self._get_response_conde(exception)
                    ).observe(elapsed)
            CLIENT_IN_PROGRESS_REQUESTS.labels(
                servicer.name(),
                self._remote_service_name,
                call_details.method
            ).dec()

        try:
            before_request()
            response = continuation(new_details, request)
            response.add_done_callback(process_response)
        except Exception as e:
            if not issubclass(type(e), grpc.Call):
                logging.exception("Unknown exception")
            process_response(None, e)
            raise
        return response

