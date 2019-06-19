from rpc_lib import service_config_pb2

def service_descriptor_for_service_def(service_definition):
    proto_path = service_definition.proto_path.split("/")
    proto_file_name = proto_path.pop().split('.')
    if len(proto_file_name) != 2 or proto_file_name[-1] != "proto":
        return None
    proto_file_name.pop()
    module_file_name = ".".join(proto_path + [proto_file_name[0] + "_pb2"])
    service_name = (service_definition.service_name or
            ''.join(map(lambda w: w.capitalize(), proto_file_name[0].split('_'))))
    try:
        module = __import__(module_file_name, fromlist=["DESCRIPTOR"])
    except:
        logging.exception("Could not import 'DESCRIPTOR' from %s", module_file_name)
        raise
    return module.DESCRIPTOR.services_by_name[service_name]

def service_definition_and_descriptor(services_enum, service):
    service_definition = services_enum.DESCRIPTOR.values_by_number[service].GetOptions().Extensions[service_config_pb2.service_definition]
    return service_definition, service_descriptor_for_service_def(service_definition)

def service_definition(services_enum, service):
    return services_enum.DESCRIPTOR.values_by_number[service].GetOptions().Extensions[service_config_pb2.service_definition]


