from rpc_lib import call_info_pb2
from rpc_lib.common import servicer


def client_phone_equals_to(phone, *args, **kwargs):
    trace_info = servicer.current_context().trace_info
    if isinstance(trace_info, call_info_pb2.TraceInfo):
        return trace_info.client.phone == phone
    return False



