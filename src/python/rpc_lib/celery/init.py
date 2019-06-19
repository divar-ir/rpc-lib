from rpc_lib.celery import signals_impl

def init_celery(service_name, prometheus_port=9000):
    signals_impl.connect_signals(service_name, prometheus_port)
