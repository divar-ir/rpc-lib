from concurrent import futures
import grpc

from rpc_lib.common.servicer import init
from rpc_lib.common.prometheus_metrics import SERVER_FREE_WORKERS
from rpc_lib.common.context_holder.thread import ThreadContextHolder
from rpc_lib.grpc_server.interceptor import ServerContextInterceptor

def init_grpc_server(service_name, workers, port, interceptors = []):
    init(service_name, ThreadContextHolder())

    SERVER_FREE_WORKERS.labels(service_name, 'grpc').set(workers)

    interceptors = interceptors + [ServerContextInterceptor()]
    thread_pool = futures.ThreadPoolExecutor(max_workers=workers)
    grpc_server = grpc.server(thread_pool, interceptors=interceptors)
    grpc_server.add_insecure_port(port)

    return grpc_server



