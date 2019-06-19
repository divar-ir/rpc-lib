from google.protobuf import json_format
import logging
from rpc_lib.common import servicer

from rpc_lib.config import flags_pb2
from rpc_lib.config.modules import modules


class FlagWrapper:
    def __init__(self, flag_def):
        self._flag_def = flag_def

    @property
    def flag_def(self):
        return self._flag_def

    def _to_value(self, v):
        if self._flag_def.type == flags_pb2.STRING:
            return v.string_value
        if self._flag_def.type == flags_pb2.BOOLEAN:
            return v.bool_value
        if self._flag_def.type == flags_pb2.INTEGER:
            return int(v.number_value)
        if self._flag_def.type == flags_pb2.FLOAT:
            return v.number_value
        raise Exception("Not implemented")

    def _effective_flag_def(self):
        experiments = []
        context = servicer.current_context()
        if context is not None:
            experiments = context.get_or_create_state().experiments
        config_wrapper = modules.global_config_wrapper
        config_flag_def = config_wrapper and config_wrapper.flag_def(self._flag_def.name, experiments)
        return config_flag_def or self._flag_def

    def evaluate(self):
        flag_def = self._effective_flag_def()
        conditions_manager = modules.conditions_manager
        if conditions_manager is not None:
            for ovr in flag_def.value.overrides:
                if conditions_manager.evaluate(ovr.condition):
                    return self._to_value(ovr.value)
        else:
            # TODO: log error
            pass
        return self._to_value(flag_def.value.base_value)


class FlagsManager:
    class FlagsHolder:
        def __init__(self, flag_manager):
            self._flag_manager = flag_manager

        def __getattr__(self, name):
            flag = self._flag_manager.get_flag(name)
            if flag is None:
                raise Exception("Access to undefined flag %s" % name)
            return flag.evaluate()

    def __init__(self):
        self._flags = {}
        self.flags_holder = FlagsManager.FlagsHolder(self)

    def _register_flag_def(self, flag):
        if self._flags.get(flag.name):
            raise Exception("Flag %s already defined", flag.name)
        # TODO: sanity check flag value
        self._flags[flag.name] = FlagWrapper(flag)

        config_wrapper = modules.global_config_wrapper
        if config_wrapper:
            try:
                config_wrapper.set_flags_defs()
            except Exception:
                try:
                    logging.exception("Could not apply flag defs from config")
                except Exception:
                    pass

        return self._flags[flag.name]

    def remove_all_flags(self):
        # To be called only by unit-tests.
        self._flags = {}

    def get_flag(self, name):
        return self._flags.get(name)

    def register_flag(self, name, type, base_value, overrides):
        flag = flags_pb2.FlagDefinition(name=name, type=type)
        json_format.ParseDict(dict(base_value=base_value, overrides=overrides or []), flag.value)
        return self._register_flag_def(flag)
