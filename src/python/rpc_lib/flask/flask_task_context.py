from rpc_lib.common.task_context import TaskContext


class FlaskTaskContext(TaskContext):
    def __init__(self, request_state, trace_info):
        super(FlaskTaskContext, self).__init__(request_state, trace_info=trace_info)
