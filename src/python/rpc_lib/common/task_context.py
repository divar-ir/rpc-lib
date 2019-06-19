import base64
import json

from rpc_lib.common import specialization
from rpc_lib import call_info_pb2


class TaskContext(object):
    def __init__(self, request_state=None, rpc_info=None, trace_info=None):
        self.request_state = request_state
        self.rpc_info = rpc_info or call_info_pb2.RpcInfo()
        self.trace_info = trace_info
        self.updated_state = False

    def time_remaining(self):
        return None

    def update_state(self, request_state):
        self.request_state = request_state
        self.updated_state = True

    def get_or_create_state(self):
        if self.request_state is None:
            self.request_state = specialization.create_state_proto()
        return self.request_state
