import grpc
from kombu import BrokerConnection

from rpc_lib.common.servicer import init
from rpc_lib.common.prometheus_metrics import SERVER_FREE_WORKERS
from rpc_lib.common.context_holder.thread import ThreadContextHolder
from rpc_lib.rabbitmq.server import RabbitMQServer
from rpc_lib.rabbitmq.retry_coordinator import RetryCoordinator

def init_rabbitmq_server(service_name, workers, services_enum, endpoint, exchange_name='rpc', transport_options=None,
    retry_coordinator=RetryCoordinator(), retry_deadletter_ttl=1.0, **init_kw_args):

    init(service_name, ThreadContextHolder(), **init_kw_args)

    SERVER_FREE_WORKERS.labels(service_name, 'rabbitmq').set(workers)

    connection = BrokerConnection(endpoint, transport_options=transport_options)
    server = RabbitMQServer(workers, services_enum, exchange_name, connection, retry_coordinator, retry_deadletter_ttl=retry_deadletter_ttl)

    return server
