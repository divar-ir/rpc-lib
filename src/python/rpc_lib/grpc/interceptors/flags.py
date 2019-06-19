import logging
import datetime

from rpc_lib import call_info_pb2
from rpc_lib.common import specialization
from rpc_lib.grpc.interceptors.utils import extract_request_and_context
from rpc_lib.grpc_server.grpc_task_context import REQUEST_STATE, TRACE_INFO, RPC_INFO
from rpc_lib.third_party import client_call_details
from rpc_lib.third_party import generic_client_interceptor
from rpc_lib.util import proto_encoding

def _get_metadata(metadata, metadata_key):
    if not metadata: return None
    for key, value in metadata:
        if key == metadata_key:
            return value

def flags_interceptor():
    def response_handler(task_context):
        def _process_result(result):
            if result.exception() is not None:
                return
            try:
                state_bin = _get_metadata(result.trailing_metadata(), REQUEST_STATE)
                if state_bin is not None:
                    request_state = proto_encoding.decode(specialization.create_state_proto(), state_bin)
                    task_context.update_state(request_state)
            except Exception:
                logging.exception("Error in handling response")
        def _handle(response):
            try:
                response.add_done_callback(_process_result)
            except Exception:
                logging.exception("Error in attaching callback to response")
            return response
        return _handle

    def intercept_call(call_details, request, request_iterator, response_streaming):
        _, task_context = extract_request_and_context(request)

        metadata = []
        if task_context is not None and task_context.request_state is not None:
            metadata.append((
                REQUEST_STATE,
                proto_encoding.encode(task_context.request_state),
            ))

        rpc_info = call_info_pb2.RpcInfo()
        rpc_info.ts.FromDatetime(datetime.datetime.utcnow())
        metadata.append((
            RPC_INFO,
            proto_encoding.encode(rpc_info),
          ))


        trace_info = task_context.trace_info if task_context else None
        if trace_info:
            metadata.append((
                TRACE_INFO,
                proto_encoding.encode(trace_info),
              ))

        if metadata:
            if call_details.metadata is not None:
                metadata = list(call_details.metadata) + metadata
            call_details = client_call_details.create(
                call_details.method, call_details.timeout, metadata,
                call_details.credentials, call_details.wait_for_ready)

        return call_details, request, request_iterator, \
                response_handler(task_context) if task_context is not None else None

    return generic_client_interceptor.create(intercept_call)


