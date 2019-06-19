from rpc_lib.common.servicer import init
from rpc_lib.common.prometheus_metrics import SERVER_FREE_WORKERS
from rpc_lib.common.context_holder.thread import ThreadContextHolder
from rpc_lib.flask.middleware import apply_middlewares


def init_flask(service_name, app, **init_kwargs):
    init(service_name, ThreadContextHolder(), **init_kwargs)
    SERVER_FREE_WORKERS.labels(service_name, 'flask').set(1)
    apply_middlewares(app)
