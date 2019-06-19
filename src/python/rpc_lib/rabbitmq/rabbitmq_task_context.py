from rpc_lib import call_info_pb2
from rpc_lib.common import specialization
from rpc_lib.common.task_context import TaskContext
from rpc_lib.util import proto_encoding

class RabbitMQTaskContext(TaskContext):
    def __init__(self, rabbitmq_request, rabbitmq_service_context):
        request_state = specialization.create_state_proto()
        request_state.ParseFromString(rabbitmq_request.experiments_data)
        self._service_context = rabbitmq_service_context

        super(RabbitMQTaskContext, self).__init__(request_state,
                rabbitmq_request.rpc_info if rabbitmq_request.HasField("rpc_info") else None,
                rabbitmq_request.trace_info if rabbitmq_request.HasField("trace_info") else None)

    def time_remaining(self):
        if not self._service_context.is_active():
            return 0
        return self._service_context.time_remaining()
