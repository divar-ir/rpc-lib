from amqp.exceptions import ConnectionError
from concurrent.futures import ThreadPoolExecutor
import copy
import functools
from kombu import Exchange, Queue, Message
from kombu.connection import ConnectionPool
from kombu.mixins import ConsumerMixin
import grpc
import logging
import threading
import time
from datetime import datetime
try:
    import queue
except ImportError:
    import Queue as queue

from rpc_lib import rabbitmq_pb2
from rpc_lib.common import servicer
from rpc_lib.util import service_config_utils
from rpc_lib.rabbitmq.rabbitmq_servicer_context import RabbitMQServicerContext
from rpc_lib.rabbitmq.rabbitmq_task_context import RabbitMQTaskContext
from rpc_lib.grpc_server.grpc_task_context import REQUEST_STATE
from rpc_lib.common.prometheus_metrics import SERVER_LATENCY, SERVER_STATUS_CODE, SERVER_IN_PROGRESS, SERVER_FREE_WORKERS, JOB_LATENCY, JOB_RETRIES

class RabbitMQServer(object):
    def __init__(self, num_workers, services_enum, exchange_name, connection, retry_coordinator, retry_deadletter_ttl=1.0):
        self._services_enum = services_enum
        self._service_func_by_method_fullname = {}
        self._method_by_method_fullname = {}
        self._queues = []
        self._exchange = Exchange(exchange_name, type="topic")
        self._executor = ThreadPoolExecutor(max_workers=num_workers)
        self._prefetch_count = 2*num_workers
        self._connection_pool = ConnectionPool(connection, 5)
        self._connection = connection.clone()
        self._retry_coordinator = retry_coordinator
        self._retry_deadletter_ttl = retry_deadletter_ttl

    def add_servicer(self, service, servicer):
        service_definition, service_descriptor = service_config_utils.service_definition_and_descriptor(self._services_enum, service)

        routing_key = "rpc.%s.%s.*" % (service_definition.name, service_descriptor.full_name)
        queue_name = "rpc.%s.%s" % (service_definition.name, service_descriptor.full_name)
        queue = Queue(queue_name, self._exchange, routing_key=routing_key)
        self._queues.append(queue)

        for method in service_descriptor.methods:
            if hasattr(servicer, method.name):
                if self._service_func_by_method_fullname.get(method.full_name):
                    raise Exception("Duplicate handler for method %s" % method.full_name)
                self._method_by_method_fullname['/' + method.full_name] = method
                self._service_func_by_method_fullname['/' + method.full_name] = getattr(servicer, method.name)

    def requeue_with_retry(self, retry_left, *args):
        with self._connection_pool.acquire(block=True) as connection:
            try:
                return self._requeue_with_connection(connection, *args)
            except:
                if retry_left < 1:
                    raise

        return self.requeue_with_retry(retry_left - 1, *args)

    @staticmethod
    def _requeue_with_connection(connection, queue_name, headers, request_binary):
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
                         routing_key=queue_name,
                         content_type="protobuf",
                         delivery_mode=2)
        return True




    class Worker(ConsumerMixin, threading.Thread):
        def __init__(self, server):
            self._server = server
            self._msg_opr_queue = queue.Queue()
            self._requested_stop = False
            self._in_progress = 0
            super(RabbitMQServer.Worker, self).__init__()

        def stop_worker(self):
            self._requested_stop = True

        @property
        def connection(self):
            return self._server._connection

        def get_consumers(self, Consumer, channel):
            return [Consumer(q, prefetch_count=self._server._prefetch_count, callbacks = [functools.partial(self.on_message, q.name)])
                    for q in self._server._queues]

        def on_message(self, queue_name, body, message):
            self._server._executor.submit(self._try_on_message, queue_name, body, message)

        def _requeue(self, queue_name, body, message, retry_cnt, execute_at):
            headers = copy.deepcopy(message.headers)
            if retry_cnt is not None:
                headers['retry_cnt'] = str(retry_cnt)
            if execute_at is not None:
                headers['execute_at'] = execute_at
            self._server.requeue_with_retry(3, queue_name, headers, body)

        def _try_on_message(self, *args):
            try:
                SERVER_FREE_WORKERS.labels(servicer.name(), 'rabbitmq').dec()
                SERVER_IN_PROGRESS.labels(servicer.name(), 'rabbitmq').inc()
                self._in_progress += 1

                self._on_message(*args)
            except:
                logging.exception("Unrecoverable exception while handling message")
            finally:
                SERVER_FREE_WORKERS.labels(servicer.name(), 'rabbitmq').inc()
                SERVER_IN_PROGRESS.labels(servicer.name(), 'rabbitmq').dec()
                self._in_progress -= 1

        @staticmethod
        def _ack_message(message):
            did_ack = False
            if message.channel.connection:
                try:
                    message.ack()
                    did_ack = True
                except ConnectionError:
                    pass
            if not did_ack:
                logging.warning('Failed to ack rabbitmq message')

        @staticmethod
        def _reject_message(message):
            logging.info('Rejecting message')
            if message.channel.connection:
                try:
                    message.reject()
                    did_reject = True
                except ConnectionError:
                    logging.exception('Failed to reject rabbitmq message since conntion is closed.')
            else:
                logging.warning('Failed to reject rabbitmq message since conntion is closed.')

        def on_iteration(self):
            set_should_stop = False
            if self._requested_stop and self._in_progress == 0:
                set_should_stop = True
            while not self._msg_opr_queue.empty():
                todo = self._msg_opr_queue.get_nowait()
                todo[0](*todo[1:])
            if set_should_stop:
                self.should_stop = True
            
        def _on_message(self, queue_name, body, message):
            if not message.channel.connection:
                return
            retry_cnt = int(message.headers.get('retry_cnt', '0'))

            service_context = RabbitMQServicerContext(30)
            start_time = None
            try:
                method_name = message.headers.get('method')
                execute_at = message.headers.get('execute_at')
                rabbitmq_request = rabbitmq_pb2.RabbitMqRpcMessage()
                job_timestamp = None
                caller_service_name = None
                rpc_info = None

                if execute_at and not RabbitMQServer._should_execute(int(execute_at)):
                    self._msg_opr_queue.put((self._requeue, RabbitMQServer._retry_queue_name(queue_name), body, message, None, None))
                    self._msg_opr_queue.put((self._ack_message, message))
                    return

                if method_name:
                    request_body = body

                    method_name = '/' + method_name
                    state_bin = message.headers.get(REQUEST_STATE)
                    if state_bin is not None:
                        rabbitmq_request.experiments_data = state_bin.encode()
                else:
                    rabbitmq_request.ParseFromString(body)
                    method_name = rabbitmq_request.rpc_info.method
                    request_body = rabbitmq_request.request
                    job_timestamp = time.mktime(rabbitmq_request.rpc_info.ts.ToDatetime().timetuple())
                    caller_service_name = rabbitmq_request.rpc_info.caller_service
                    rpc_info = rabbitmq_request.rpc_info

                if retry_cnt == 0 and rabbitmq_request.rpc_info.HasField("target_ts"):
                    target_ts = rabbitmq_request.rpc_info.target_ts.ToDatetime()
                else:
                    target_ts = datetime.utcnow()

                if datetime.utcnow() < target_ts:
                    self._msg_opr_queue.put((self._requeue, RabbitMQServer._retry_queue_name(queue_name), body, message, retry_cnt, rabbitmq_request.rpc_info.target_ts.ToMilliseconds()))
                    self._msg_opr_queue.put((self._ack_message, message))
                    return

                task_context = RabbitMQTaskContext(rabbitmq_request, service_context)
                servicer.set_current_context(task_context)

                start_time = time.time()
                input_msg = self._server._method_by_method_fullname[method_name].input_type._concrete_class()
                input_msg.ParseFromString(request_body)
                servicer_func = self._server._service_func_by_method_fullname[method_name]
                servicer_func(input_msg, service_context)

            except RabbitMQServicerContext.Finished:
                pass
            except Exception:
                logging.exception("Exception while handling method %s", method_name)
                service_context.set_code(grpc.StatusCode.INTERNAL)

            canonical_method_name =  '/'.join(method_name.rsplit('.', 1))

            if start_time is not None:
                elapsed = time.time() - start_time
                SERVER_LATENCY.labels(servicer.name(), canonical_method_name, 'rabbitmq').observe(elapsed)
            status_code = service_context.get_code() or grpc.StatusCode.OK

            need_message_ack = True
            job_done = False
            if status_code == grpc.StatusCode.INTERNAL:
                max_retries = self._server._retry_coordinator.max_retries(rpc_info, status_code)
                if retry_cnt < max_retries:
                    try:
                        if message.channel.connection:
                            backoff = self._server._retry_coordinator.backoff(rpc_info, status_code, retry_cnt)
                            self._msg_opr_queue.put((self._requeue, RabbitMQServer._retry_queue_name(queue_name), body, message, retry_cnt+1, backoff))
                        else:
                            logging.warning('Failed to requeue rabbitmq message')
                            need_message_ack = False
                            job_done = True
                    except Exception:
                        logging.exception("Could not requeue message")
                        need_message_ack = False
                        job_done = True
                        self._msg_opr_queue.put((self._reject_message, message))
                else:
                    need_message_ack = False
                    job_done = True
                    logging.error("Rejecting message after %s retries", retry_cnt)
                    self._msg_opr_queue.put((self._reject_message, message))
            else:
                job_done = True
            if need_message_ack:
                self._msg_opr_queue.put((self._ack_message, message))
            SERVER_STATUS_CODE.labels(servicer.name(), canonical_method_name, status_code.name, 'rabbitmq').inc()

            if job_done:
                now = time.mktime(datetime.utcnow().timetuple())
                if job_timestamp:
                    JOB_LATENCY.labels(caller_service_name, servicer.name(),
                        canonical_method_name, status_code.name).observe(now - job_timestamp)
                JOB_RETRIES.labels(caller_service_name, servicer.name(),
                    canonical_method_name, status_code.name).observe(retry_cnt)

    def declare_queues(self):
        self._connection.ensure_connection()
        with self._connection.channel() as channel:
            bound_exchange = self._exchange(channel)
            bound_exchange.declare()
            for q in self._queues:
                bound_queue = q(channel)
                bound_queue.declare()

                retry_queue = Queue(
                    name=RabbitMQServer._retry_queue_name(q.name),
                    exchange=None,
                    queue_arguments={
                        'x-dead-letter-exchange': '',
                        'x-dead-letter-routing-key': q.name,
                        'x-message-ttl': int(self._retry_deadletter_ttl * 1000),
                    })
                bound_retry_queue = retry_queue(channel)
                bound_retry_queue.declare()


    def make_worker(self):
        return RabbitMQServer.Worker(self)

    def run(self):
        self.declare_queues()
        worker = self.make_worker()
        worker.start()
        return worker

    @staticmethod
    def _retry_queue_name(queue_name):
        return '{}__retry'.format(queue_name)

    @staticmethod
    def _should_execute(execute_at):
        return execute_at <= RabbitMQServer._get_timestamp()

    @staticmethod
    def _get_timestamp():
        return int(round(time.time() * 1000))

