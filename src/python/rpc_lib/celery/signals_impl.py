import logging
from base64 import b64encode, b64decode

import prometheus_client
import prometheus_client.multiprocess

from celery import Celery, signals

from rpc_lib import call_info_pb2
from rpc_lib.common import servicer
from rpc_lib.common import specialization
from rpc_lib.celery.celery_task_context import CeleryTaskContext
from rpc_lib.common.context_holder.thread import ThreadContextHolder

TRACE_INFO = "x_internal_trace_info"
REQUEST_STATE = "x_internal_state"

def task_prerun(task=None, **kwargs):
    trace_info = None
    request_state = None
    if task.request.headers is not None:
        trace_info = task.request.headers.get(TRACE_INFO)
        request_state = task.request.headers.get(REQUEST_STATE)
    if trace_info is None and hasattr(task.request, TRACE_INFO):
        trace_info = getattr(task.request, TRACE_INFO)
    if request_state is None and hasattr(task.request, REQUEST_STATE):
        request_state = getattr(task.request, REQUEST_STATE)
    if trace_info is not None:
        trace_info = call_info_pb2.TraceInfo().FromString(b64decode(trace_info))
    if request_state is not None:
        request_state = specialization.create_state_proto().FromString(b64decode(request_state))
    servicer.set_current_context(CeleryTaskContext(request_state=request_state, trace_info=trace_info))


def before_task_publish(headers=None, **kwargs):
    if headers is None:
        logging.warning("Headers in before_task_publish is None.")
        return
    task_context = servicer.current_context()
    if task_context is not None and task_context.request_state is not None:
        headers[REQUEST_STATE] = b64encode(task_context.request_state.SerializeToString())
    if task_context is not None and task_context.trace_info is not None:
        headers[TRACE_INFO] = b64encode(task_context.trace_info.SerializeToString())

# Just for passing params to siganl functions. Not sure why other methods do not work.
class WorkerParams:
    service_name = "UNKNOWN"
    prometheus_port = None

def worker_init(**kwargs):
    servicer.init(WorkerParams.service_name, ThreadContextHolder())
    if WorkerParams.prometheus_port is not None:
        registry = prometheus_client.CollectorRegistry()
        prometheus_client.multiprocess.MultiProcessCollector(registry)
        prometheus_client.start_http_server(WorkerParams.prometheus_port, registry=registry)


def worker_process_shutdown(pid=None, **kwargs):
    prometheus_client.multiprocess.mark_process_dead(pid)

def connect_signals(service_name, prometheus_port):
    WorkerParams.service_name = service_name
    WorkerParams.prometheus_port = prometheus_port

    signals.task_prerun.connect(task_prerun)
    signals.before_task_publish.connect(before_task_publish)
    signals.worker_init.connect(worker_init)
    signals.worker_process_shutdown.connect(worker_process_shutdown)

