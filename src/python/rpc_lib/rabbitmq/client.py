import datetime
import logging
import threading
import kombu
from kombu.connection import ConnectionPool

from rpc_lib import call_info_pb2, rabbitmq_pb2
from rpc_lib.common import servicer
from rpc_lib.grpc_server.grpc_task_context import REQUEST_STATE, RPC_INFO, TRACE_INFO

class RabbitMQClient(object):

    class StubV1():
        def __init__(self, rabbitmq_client, service_descriptor, service_name, instance_name, exchange):
            self._rabbitmq_client = rabbitmq_client
            self._service_descriptor = service_descriptor
            self._service_name =  service_name
            self._instance_name = instance_name
            self._exchange = exchange

        def __getattr__(self, name):
            method = self._service_descriptor.methods_by_name.get(name)
            if name is None:
                raise Exception("Unknown method %s" % name)
            def do(request, timeout=None):
                if timeout is not None:
                    logging.warning("Ignoring timeout for rabbitmq stub")
                serialized_request = method.input_type._concrete_class.SerializeToString(request)

                headers = {
                        'service': self._service_name,
                        'method': method.full_name
                        }
                context = servicer.current_context()
                if context is not None and context.request_state is not None:
                    headers[REQUEST_STATE] = context.request_state.SerializeToString()

                routing_key = "rpc.%s.%s" % (self._service_name, method.full_name)
                self._rabbitmq_client._publish_with_retry(3, self._exchange, routing_key, headers, serialized_request)
            return do

    class StubV2():
        def __init__(self, rabbitmq_client, service_descriptor, service_name, instance_name, exchange):
            self._rabbitmq_client = rabbitmq_client
            self._service_descriptor = service_descriptor
            self._service_name =  service_name
            self._instance_name = instance_name
            self._exchange = exchange

        def __getattr__(self, name):
            method = self._service_descriptor.methods_by_name.get(name)
            if name is None:
                raise Exception("Unknown method %s" % name)
            def do(request, timeout=None, delay=None):
                if timeout is not None:
                    logging.warning("Ignoring timeout for rabbitmq stub")

                rabbitmq_request = rabbitmq_pb2.RabbitMqRpcMessage()
                rabbitmq_request.request = method.input_type._concrete_class.SerializeToString(request)
                rabbitmq_request.rpc_info.method = '/' + method.full_name
                rabbitmq_request.rpc_info.caller_service = servicer.name()
                rabbitmq_request.rpc_info.ts.FromDatetime(datetime.datetime.utcnow())

                if delay is not None:
                    rabbitmq_request.rpc_info.target_ts.FromDatetime(datetime.datetime.utcnow() + delay)

                context = servicer.current_context()
                if context is not None and context.request_state is not None:
                    rabbitmq_request.experiments_data = context.request_state.SerializeToString()

                if context is not None and context.trace_info is not None:
                    rabbitmq_request.trace_info.CopyFrom(context.trace_info)

                routing_key = "rpc.%s.%s" % (self._service_name, method.full_name)
                self._rabbitmq_client._publish_with_retry(3, self._exchange, routing_key, {}, rabbitmq_request.SerializeToString())
            return do

    def __init__(self, endpoint):
        connection = kombu.Connection(endpoint, transport_options={
            'confirm_publish': False,
        })
        self._connection_pool = ConnectionPool(connection, 5)
        self._exchange_by_name = {}
        self._exchange_lock = threading.Lock()

    def _publish_with_retry(self, retry_left, *args, **kwargs):
        with self._connection_pool.acquire(block=True) as connection:
            try:
                return self._publish_with_connection(connection, *args, **kwargs)
            except:
                if retry_left < 1:
                    raise

        return self._publish_with_retry(retry_left - 1, *args, **kwargs)

    @staticmethod
    def _publish_with_connection(connection, exchange, routing_key, headers, request_binary):
        producer = connection.Producer()
        producer.publish(request_binary,
                         retry=True,
                         retry_policy={
                             'max_retries': 5,
                             'interval_start': 0,
                             'interval_step': 6,
                             'interval_max': 30,
                         },
                         headers=headers,
                         exchange=exchange,
                         routing_key=routing_key,
                         content_type="protobuf",
                         delivery_mode=2)
        return True

    def _get_exchange(self, name):
        exchange = self._exchange_by_name.get(name)
        if exchange:
            return exchange
        with self._exchange_lock:
            exchange = self._exchange_by_name.get(name)  # double check it is not created by another thread.
            if not exchange:
                exchange = kombu.Exchange(name=name,
                                          type='topic',
                                          durable=True)
                with self._connection_pool.acquire(block=True) as connection:
                    with connection.channel() as channel:
                        bound_exchange = exchange(channel)
                        bound_exchange.declare()
                self._exchange_by_name[name] = exchange
        return exchange

    def get_stub(self, service_descriptor, service_name, instance_name, instance_config):
        exchange = self._get_exchange(instance_config.exchange_name or "rpc")
        if instance_config.support_new_rabbitmq_protocol:
            return RabbitMQClient.StubV2(self, service_descriptor, service_name, instance_name, exchange)
        else:
            return RabbitMQClient.StubV1(self, service_descriptor, service_name, instance_name, exchange)


