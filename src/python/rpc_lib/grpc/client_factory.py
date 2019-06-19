from google.protobuf import json_format
import logging

from rpc_lib.config.modules import modules
from rpc_lib import service_config_pb2
from rpc_lib.common.servicer import create_grpc_client

class GrpcClientFactory(object):
    _empty_service_config = service_config_pb2.GRPCServiceConfig()

    def __init__(self, services_enum):
        self._services_enum = services_enum
        self._client_by_endpoint = {}
        self._stub_factory_by_service_id = {}
        self._config = service_config_pb2.Config()
        self._preloaded_grpc_config = {
                v.GetOptions().Extensions[service_config_pb2.service_definition].name : 
                v.GetOptions().Extensions[service_config_pb2.service_definition].preloaded_grpc_config 
                for v in self._services_enum.DESCRIPTOR.values
                if v.GetOptions().Extensions[service_config_pb2.service_definition].HasField("preloaded_grpc_config")
                }

    def set_config(self, config):
        logging.warning("loaded config: %s", json_format.MessageToDict(config))
        self._config = config

    def stub_factory_for_service(self, service_id, service_definition):
        if self._stub_factory_by_service_id.get(service_id) is not None:
            return self._stub_factory_by_service_id.get(service_id)
        proto_path = service_definition.proto_path.split("/")
        proto_file_name = proto_path.pop().split('.')
        if len(proto_file_name) != 2 or proto_file_name[-1] != "proto":
            return None
        proto_file_name.pop()
        module_file_name = ".".join(proto_path + [proto_file_name[0] + "_pb2_grpc"])
        stub_name = (service_definition.service_name or
                ''.join(map(lambda w: w.capitalize(), proto_file_name[0].split('_')))) + "Stub"
        try:
            module = __import__(module_file_name, fromlist=[stub_name])
        except:
            logging.exception("Could not import %s from %s", stub_name, module_file_name)
            raise
        self._stub_factory_by_service_id[service_id] = getattr(module, stub_name)
        return self._stub_factory_by_service_id[service_id]

    def get_stub_for_service(self, service, instance_name = None, custom_instance_config=None, **get_stub_kwargs):
        service_definition = self._services_enum.DESCRIPTOR.values_by_number[service].GetOptions().Extensions[service_config_pb2.service_definition]

        servicer_name, servicer_config = None, None

        # Find instance_config depending on service has deprecated in-proto definition or not.
        services_manager = modules.services_manager
        if services_manager:
            servicer_name, servicer_config = services_manager.get_servicer(self._services_enum.DESCRIPTOR.values_by_number[service].name, instance_name)
        if servicer_name is not None:
            if not servicer_config or not servicer_config.HasField("grpc"):
                return None
            instance_config = servicer_config.grpc
        elif service_definition.name:  # deprecated way
            servicer_name = service_definition.name
            service_config = self._config.grpc_services[service_definition.name]
            if custom_instance_config:
                instance_name = "custom"
                instance_config = custom_instance_config
            else:
                preloaded_config = self._preloaded_grpc_config.get(service_definition.name, self._empty_service_config)
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
            self._client_by_endpoint[instance_config.endpoint] = create_grpc_client(instance_config.endpoint)

        return self._client_by_endpoint.get(instance_config.endpoint).get_stub(
                self.stub_factory_for_service(service, service_definition),
                servicer_name,
                instance_name,
                **get_stub_kwargs)


