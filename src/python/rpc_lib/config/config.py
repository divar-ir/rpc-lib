from google.protobuf import json_format
from itertools import chain
import os

from rpc_lib.config.flags_pb2 import FlagDefinition
from rpc_lib.config import config_pb2
from rpc_lib.config.modules import modules


class GlobalConfigWrapper:
    def __init__(self, config_def=None):
        self._config_def = config_def or config_pb2.GlobalConfig()
        self._env_config_def = config_pb2.GlobalConfig()
        if os.environ.get('GLOBAL_CONFIG') is not None:
            json_format.Parse(os.environ.get('GLOBAL_CONFIG'), self._env_config_def)
        self.set_flags_defs()
        modules.services_manager.set_servicers(self._config_def.services_config, self._env_config_def.services_config)

    def set_flags_defs(self):
        flags_config = {}

        flags_manager = modules.flags_manager
        for f in chain(self._config_def.flags, self._env_config_def.flags):
            flag_wrapper = flags_manager.get_flag(f.name)
            if flag_wrapper is None:
                continue
            if flag_wrapper.flag_def.type != f.type:
                raise Exception("Mismatch flag type for flag %s" % f.name)
            flags_config[f.name] = f

        self._flag_config = flags_config

    def flag_def(self, name, current_experiments):
        flag_definition = self._flag_config.get(name)
        if flag_definition is None:
            return None
        for experiment_id in current_experiments:
            experiment = self._env_config_def.experiments.get(experiment_id) or self._config_def.experiments.get(experiment_id)
            if experiment is not None and name in experiment.flag_values:
                result = FlagDefinition()
                result.CopyFrom(flag_definition)
                result.value.CopyFrom(experiment.flag_values[name])
                return result
        return flag_definition


modules.register_global_config_wrapper(GlobalConfigWrapper())
