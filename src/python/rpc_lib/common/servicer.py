import logging
import prometheus_client
from rpc_lib.version import RPC_LIB_VERSION
from rpc_lib.common.context_holder.thread import ThreadContextHolder

SERVICE_INFO = prometheus_client.Gauge("rpc_service_info", "", ["service_name", "rpc_lib_version"], multiprocess_mode='max')


class Servicer(object):
    name = "UNKNOWN"
    context_holder = ThreadContextHolder()
    grpc_client_creator = None


_already_initialized = False


def init(service_name, context_holder, grpc_client_creator=None, setup_kuber_config_loader=True):
    from rpc_lib.config.loader import KuberConfigLoader

    Servicer.name = service_name
    Servicer.context_holder = context_holder
    Servicer.grpc_client_creator = grpc_client_creator

    global _already_initialized
    if _already_initialized:
        logging.warning("Multiple initialization of rpc-lib.")
    else:
        _already_initialized = True
        SERVICE_INFO.labels(service_name, RPC_LIB_VERSION).set(1)
        if setup_kuber_config_loader:
            loader = KuberConfigLoader(service_name)
            loader.load()
            loader.start_periodic_load()


def name():
    return Servicer.name


def context_holder():
    return Servicer.context_holder


def current_context():
    return Servicer.context_holder.current_context()


def set_current_context(context):
    return Servicer.context_holder.set_current_context(context)


def create_grpc_client(server_address):
    from rpc_lib.grpc.grpc_client import GrpcClient

    creator = Servicer.grpc_client_creator or GrpcClient
    return creator(server_address)
