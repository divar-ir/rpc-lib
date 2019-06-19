from flask import request
from flask.signals import request_started, request_finished, got_request_exception

from rpc_lib.common.prometheus_metrics import SERVER_FREE_WORKERS, SERVER_IN_PROGRESS
from rpc_lib.common import servicer
from rpc_lib.flask.flask_task_context import FlaskTaskContext
from rpc_lib.util import headers


def _before_request(sender, **extra):
    state = headers.get_state(request.headers)
    trace_info = headers.get_trace_info(request.headers)
    servicer.set_current_context(FlaskTaskContext(state, trace_info))
    SERVER_FREE_WORKERS.labels(servicer.name(), 'flask').dec()
    SERVER_IN_PROGRESS.labels(servicer.name(), 'flask').inc()


def _after_request(sender, response, **extra):
    SERVER_FREE_WORKERS.labels(servicer.name(), 'flask').inc()
    SERVER_IN_PROGRESS.labels(servicer.name(), 'flask').dec()


def _after_exception(sender, exception, **extra):
    SERVER_FREE_WORKERS.labels(servicer.name(), 'flask').inc()
    SERVER_IN_PROGRESS.labels(servicer.name(), 'flask').dec()


def apply_middlewares(app):
    request_started.connect(_before_request, sender=app)
    request_finished.connect(_after_request, sender=app)
    got_request_exception.connect(_after_exception, sender=app)
