from rpc_lib.common.task_context import TaskContext

class CeleryTaskContext(TaskContext):
    def __init__(self, request_state, trace_info):
        super(CeleryTaskContext, self).__init__(request_state=request_state, trace_info=trace_info)

