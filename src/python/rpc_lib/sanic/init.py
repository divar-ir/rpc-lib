from rpc_lib.common.servicer import init
from rpc_lib.common.prometheus_metrics import SERVER_FREE_WORKERS
from rpc_lib.sanic.middleware import apply_middlewares
from rpc_lib.sanic.grpc_client_creator import SanicGrpcClientFactory
from rpc_lib.common.context_holder.task import TaskContextHolder

def init_sanic(service_name, app, async_grpc_calls=True, **init_kwargs):
    def before_start(app, loop):
        SanicGrpcClientFactory.sanic_app = app
        grpc_client_creator = None
        if async_grpc_calls:
            grpc_client_creator = SanicGrpcClientFactory.create_grpc_client
        init(service_name, TaskContextHolder(loop), grpc_client_creator, **init_kwargs)
        SERVER_FREE_WORKERS.labels(service_name, 'sanic').set(1)
        apply_middlewares(app)

    app.listener('before_server_start')(before_start)

