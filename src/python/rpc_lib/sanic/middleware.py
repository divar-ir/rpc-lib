from rpc_lib.common import servicer
from rpc_lib.common.prometheus_metrics import SERVER_FREE_WORKERS, SERVER_IN_PROGRESS
from rpc_lib.sanic.sanic_task_context import SanicTaskContext
from rpc_lib.util import headers


def _before_request(request):
    state = headers.get_state(request.headers)
    trace_info = headers.get_trace_info(request.headers)
    servicer.set_current_context(SanicTaskContext(state, trace_info))
    SERVER_FREE_WORKERS.labels(servicer.name(), 'sanic').dec()
    SERVER_IN_PROGRESS.labels(servicer.name(), 'sanic').inc()


def _after_request(request, response):
    SERVER_FREE_WORKERS.labels(servicer.name(), 'sanic').inc()
    SERVER_IN_PROGRESS.labels(servicer.name(), 'sanic').dec()


def apply_middlewares(app):
    app.register_middleware(_before_request, attach_to='request')
    app.register_middleware(_after_request, attach_to='response')
