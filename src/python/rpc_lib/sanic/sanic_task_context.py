from rpc_lib.common.task_context import TaskContext


class SanicTaskContext(TaskContext):
    def __init__(self, request_state, trace_info):
        super(SanicTaskContext, self).__init__(request_state, trace_info=trace_info)
