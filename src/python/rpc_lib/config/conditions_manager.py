from google.protobuf import json_format

from rpc_lib.config.modules import modules
from rpc_lib.config.pre_defined_conditions import client_phone_equals_to

class ConditionsManager:
    def __init__(self):
        self._condition_handlers = {}

    def register_condition_handler(self, condition_name, handler):
        self._condition_handlers[condition_name] = handler

    def evaluate(self, condition):
        handler = self._condition_handlers.get(condition.condition_name)
        if handler is None:
            # TODO: log error
            return False
        return handler(**json_format.MessageToDict(condition).get("params", {}))


modules.register_conditions_manager(ConditionsManager())

modules.conditions_manager.register_condition_handler('client_phone_equals_to', client_phone_equals_to)
