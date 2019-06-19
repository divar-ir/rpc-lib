from rpc_lib.common.servicer import init
from rpc_lib.common.prometheus_metrics import SERVER_FREE_WORKERS
from rpc_lib.common.context_holder.thread import ThreadContextHolder


def init_django(service_name, setup_k8s_config_loader=True):
    init(
        service_name,
        ThreadContextHolder(),
        setup_kuber_config_loader=setup_k8s_config_loader
    )
    SERVER_FREE_WORKERS.labels(service_name, 'django').set(1)
