from google.protobuf import json_format
import logging

from rpc_lib.config.modules import modules
from rpc_lib import service_config_pb2
from rpc_lib.rabbitmq.client import RabbitMQClient
from rpc_lib.util import service_config_utils

class RabbitMQClientFactory(object):
    _empty_service_config = service_config_pb2.RabbitMQServiceConfig()

    def __init__(self, services_enum):
        self._services_enum = services_enum
        self._client_by_endpoint = {}
        self._service_descriptor_by_service_id = {}
        self._config = service_config_pb2.Config()
        self._preloaded_rabbitmq_config = {
                v.GetOptions().Extensions[service_config_pb2.service_definition].name : 
                v.GetOptions().Extensions[service_config_pb2.service_definition].preloaded_rabbitmq_config 
                for v in self._services_enum.DESCRIPTOR.values
                if v.GetOptions().Extensions[service_config_pb2.service_definition].HasField("preloaded_rabbitmq_config")
                }

    def set_config(self, config):
        logging.warning("loaded config: %s", json_format.MessageToDict(config))
        self._config = config

    def select_service_instance(self, service_name):
        return ""

    def service_descriptor_for_service_def(self, service_id, service_definition):
        if self._service_descriptor_by_service_id.get(service_id) is not None:
            return self._service_descriptor_by_service_id.get(service_id)
        self._service_descriptor_by_service_id[service_id] = service_config_utils.service_descriptor_for_service_def(service_definition)
        return self._service_descriptor_by_service_id[service_id]

    def get_stub_for_service(self, service, instance_name = None, custom_instance_config=None, **get_stub_kwargs):
        service_definition = self._services_enum.DESCRIPTOR.values_by_number[service].GetOptions().Extensions[service_config_pb2.service_definition]

        servicer_name, servicer_config = None, None

        # Find instance_config depending on service has deprecated in-proto definition or not.
        services_manager = modules.services_manager
        if services_manager:
            servicer_name, servicer_config = services_manager.get_servicer(self._services_enum.DESCRIPTOR.values_by_number[service].name, instance_name)
        if servicer_name is not None:
            if not servicer_config or not servicer_config.HasField("rabbitmq"):
                return None
            instance_config = servicer_config.rabbitmq
        elif service_definition.name:  # deprecated way
            servicer_name = service_definition.name
            service_config = self._config.rabbitmq_services[service_definition.name]
            if custom_instance_config:
                assert instance_name is not None
                instance_config = custom_instance_config
            else:
                preloaded_config = self._preloaded_rabbitmq_config.get(service_definition.name, self._empty_service_config)
                if instance_name:
                    instance_config = service_config.other_instances.get(instance_name) or preloaded_config.other_instances.get(instance_name)
                else:
                    instance_config = service_config.default_instance if service_config.HasField("default_instance") else preloaded_config.default_instance
            if not instance_config or not instance_config.endpoint:
                return None
        else:
            return None

        instance_name = instance_name or "default"
        if not self._client_by_endpoint.get(instance_config.endpoint):
            self._client_by_endpoint[instance_config.endpoint] = RabbitMQClient(instance_config.endpoint)

        return self._client_by_endpoint.get(instance_config.endpoint).get_stub(
                self.service_descriptor_for_service_def(service, service_definition),
                servicer_name,
                instance_name,
                instance_config,
                **get_stub_kwargs)


