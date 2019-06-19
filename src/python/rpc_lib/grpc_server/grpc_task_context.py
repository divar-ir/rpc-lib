from rpc_lib import call_info_pb2
from rpc_lib.common import specialization
from rpc_lib.common.task_context import TaskContext
from rpc_lib.util import proto_encoding

REQUEST_STATE = 'x-internal-state-bin'
RPC_INFO = 'x-rpc-info-bin'
TRACE_INFO = 'x-trace-info-bin'

class GrpcTaskContext(TaskContext):
    def __init__(self, grpc_context):
        request_state = None

        state_bin = self._get_metadata(grpc_context, REQUEST_STATE)
        request_state = proto_encoding.decode(specialization.create_state_proto(), state_bin)

        rpc_info_bin = self._get_metadata(grpc_context, RPC_INFO)
        rpc_info = proto_encoding.decode(call_info_pb2.RpcInfo(), rpc_info_bin) if rpc_info_bin is not None else None

        trace_info_bin = self._get_metadata(grpc_context, TRACE_INFO)
        trace_info = proto_encoding.decode(call_info_pb2.TraceInfo(), trace_info_bin) if trace_info_bin is not None else None

        super(GrpcTaskContext, self).__init__(request_state, rpc_info, trace_info)
        self._grpc_context = grpc_context

    def response_metadata(self):
        if not self.updated_state:
            return None
        return [(REQUEST_STATE, proto_encoding.encode(self.request_state))]

    def time_remaining(self):
        if not self._grpc_context.is_active():
            return 0
        return self._grpc_context.time_remaining()

    @staticmethod
    def _get_metadata(grpc_context, metadata_key):
        for key, value in grpc_context.invocation_metadata():
            if key == metadata_key:
                return value

