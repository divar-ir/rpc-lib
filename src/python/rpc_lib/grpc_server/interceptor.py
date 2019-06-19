import grpc
import time

from rpc_lib.common.prometheus_metrics import SERVER_LATENCY, SERVER_IN_PROGRESS, SERVER_FREE_WORKERS
from rpc_lib.common import servicer
from rpc_lib.grpc_server.grpc_task_context import GrpcTaskContext

class ServerContextInterceptor(grpc.ServerInterceptor):
    def __init__(self):
        super(ServerContextInterceptor, self).__init__()

    def intercept_service(self, continuation, handler_call_details):
        handler = continuation(handler_call_details)
        if not handler or not handler.unary_unary:
            return handler

        def setup_context(request, context):
            task_context = GrpcTaskContext(context)
            servicer.set_current_context(task_context)
            start_time = time.time()
            SERVER_FREE_WORKERS.labels(servicer.name(), 'grpc').dec()
            SERVER_IN_PROGRESS.labels(servicer.name(), 'grpc').inc()
            try:
                response = handler.unary_unary(request, context)
                response_metadata = task_context.response_metadata()
                if response_metadata:
                    context.set_trailing_metadata(response_metadata)
            finally:
                servicer.set_current_context(None)
                SERVER_FREE_WORKERS.labels(servicer.name(), 'grpc').inc()
                SERVER_IN_PROGRESS.labels(servicer.name(), 'grpc').dec()
                elapsed = time.time() - start_time
                SERVER_LATENCY.labels(
                        servicer.name(), handler_call_details.method, 'grpc').observe(elapsed)
            return response

        return grpc.unary_unary_rpc_method_handler(
                setup_context,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer)
