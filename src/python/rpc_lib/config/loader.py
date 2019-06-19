import base64
import datetime
import logging
import kubernetes
import prometheus_client
import threading
import time
from rpc_lib.common import specialization
from rpc_lib.config import config_pb2
from rpc_lib.config.flags import FLAGS, DEFINE_FLOAT_FLAG
from rpc_lib.config.config import GlobalConfigWrapper
from rpc_lib.config.modules import modules

DEFINE_FLOAT_FLAG("global_config_reload_period_secs", 30)

GLOBAL_CONFIG_TS = prometheus_client.Gauge("global_config_ts", "", ["service_name"], multiprocess_mode='liveall')


class KuberConfigLoader():
    def __init__(self, service_name, in_cluser=True):
        self._k8s_api = None
        self._timerThread = None
        self._last_loaded = None
        self._service_name = service_name
        self._in_cluster = in_cluser
        GLOBAL_CONFIG_TS.labels(self._service_name).set(0)

    def _ensure_k8s_api(self):
        if self._k8s_api:
            return
        if self._in_cluster:
            kubernetes.config.load_incluster_config()
        else:
            kubernetes.config.load_kube_config()
        self._k8s_api = kubernetes.client.CoreV1Api()

    def load(self):
        self._ensure_k8s_api()
        config_map_namespace, config_map_name = specialization.get_kuber_global_config()
        configmap = self._k8s_api.read_namespaced_config_map(config_map_name, config_map_namespace)
        if 'config.bin' in configmap.data:
            config_bin = configmap.data['config.bin'].encode()
        else:
            config_bin = base64.decodestring(configmap.binary_data['config.bin'].encode())
        config = config_pb2.GlobalConfig()
        config.ParseFromString(config_bin)
        self.load_config(config)

        ts = int(configmap.data['ts'])
        GLOBAL_CONFIG_TS.labels(self._service_name).set(ts * 1000)

    def safe_load(self):
        try:
            self.load()
        except Exception:
            try:
                logging.exception("Error in loading global-config")
            except Exception:
                pass

    def _periodic_load(self):
        self.safe_load()
        time.sleep(1)
        while True:
            self.safe_load()
            time.sleep(FLAGS.global_config_reload_period_secs)

    def start_periodic_load(self):
        if self._timerThread:
            self._timerThread.stop()
        self._timerThread = threading.Thread(target=self._periodic_load)
        self._timerThread.daemon = True
        self._timerThread.start()

    def load_config(self, config):
        modules.register_global_config_wrapper(GlobalConfigWrapper(config))
