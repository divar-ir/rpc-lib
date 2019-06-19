from rpc_lib import call_info_pb2
from rpc_lib.common import specialization
from rpc_lib.util.proto_encoding import decode_from_base64

HTTP_INTERNAL_STATE_HEADER = 'x-internal-state-bin'
HTTP_INTERNAL_TRACE_INFO_HEADER = 'x-internal-trace-info-bin'


def get_state(headers):
    encoded_state = headers.get(HTTP_INTERNAL_STATE_HEADER)
    return decode_from_base64(specialization.create_state_proto(), encoded_state)


def get_trace_info(headers):
    encoded_trace_info = headers.get(HTTP_INTERNAL_TRACE_INFO_HEADER)
    return decode_from_base64(call_info_pb2.TraceInfo(), encoded_trace_info)
