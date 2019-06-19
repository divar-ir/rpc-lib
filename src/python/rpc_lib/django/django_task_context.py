from rpc_lib.common.task_context import TaskContext

class DjangoTaskContext(TaskContext):
    def __init__(self):
        super(DjangoTaskContext, self).__init__()

