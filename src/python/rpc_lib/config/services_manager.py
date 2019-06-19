from itertools import chain

from rpc_lib.config.modules import modules
from rpc_lib.config import flags

class ServicesManager:
    def __init__(self):
        self._service_servicer = {}
        self._servicers = {}

    def set_servicers(self, services_config, env_services_config):
        self._service_servicer = {}
        self._servicers = services_config.servicers
        self._env_servicers = env_services_config.servicers
        for servicer_name in chain(services_config.servicers, env_services_config.servicers):
            servicer_config = env_services_config.servicers.get(servicer_name) or services_config.servicers.get(servicer_name)
            for service in servicer_config.services:
                self._service_servicer[service] = servicer_name

    def get_servicer(self, service_name, label):
        flag_name = 'servicer_' + service_name
        flag = modules.flags_manager.get_flag(flag_name) or flags.DEFINE_STRING_FLAG(flag_name)
        servicer_name = flag.evaluate() or label or self._service_servicer.get(service_name)
        if servicer_name is None:
            return None, None
        config = (self._env_servicers.get(servicer_name) or self._servicers.get(servicer_name))
        # TODO: remove hanling of this special case when completely removed deprecated service definition.
        if servicer_name == label and config is None:
            return None, None
        return servicer_name, config

modules.register_services_manager(ServicesManager())
