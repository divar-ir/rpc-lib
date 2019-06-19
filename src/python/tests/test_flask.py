import base64
import unittest
from time import sleep

import requests
from rpc_lib.config.experiments_pb2 import ExperimentDefinition
from rpc_lib.config.flags_pb2 import FlagValue
from flask.app import Flask
from flask import jsonify
from multiprocessing import Process

from rpc_lib.config import flags, config_pb2
from rpc_lib.config.loader import KuberConfigLoader
from rpc_lib.config.modules import modules
from rpc_lib.common import servicer
from rpc_lib.flask.init import init_flask


def test_api():
    return jsonify({
        'test': flags.FLAGS.test,
        'trace_info': {
            'client': {
                'ip': servicer.current_context().trace_info.client.ip,
                'phone': servicer.current_context().trace_info.client.phone
            }
        }
    })


class TestFlask(unittest.TestCase):
    app = None

    def setUp(self):
        modules.flags_manager.remove_all_flags()

        self.app = Flask(__name__)
        self.app.add_url_rule('/test', 'test', test_api, methods=['POST'])

        init_flask('test_app', self.app, setup_kuber_config_loader=False)

        flags.DEFINE_INTEGER_FLAG("test")
        self.loader = KuberConfigLoader("test_service")
        self.loader.load_config(config_pb2.GlobalConfig(
            flags=[{
                "name": "test",
                "type": "INTEGER",
                "value": {
                    "base_value": {
                        "number_value": 1
                    }
                }
            }],
            experiments={
                2: ExperimentDefinition(
                    id=2,
                    flag_values={
                        "test": FlagValue(base_value={
                            "number_value": 2
                        })
                    }
                )
            }
        ))

        self.server = Process(target=self.app.run, args=("127.0.0.1", 8008))
        self.server.start()
        sleep(1)

    def tearDown(self):
        self.server.terminate()

    def test_experiments(self):
        headers = {
            'x-internal-state-bin': 'EgA='  # experiments: []
        }
        data = requests.post(url='http://127.0.0.1:8008/test', headers=headers).json()
        self.assertEqual(data['test'], 1)

        headers = {
            'x-internal-state-bin': 'EgEC'  # experiments: [2]
        }
        data = requests.post(url='http://127.0.0.1:8008/test', headers=headers).json()
        self.assertEqual(data['test'], 2)

    def test_trace_info(self):
        headers = {
            'x-internal-trace-info-bin': 'ChYSCzA5MTIzNDU2Nzg5CgcxLjIuMy40'  # ip: 1.2.3.4, phone: 09123456789
        }
        data = requests.post(url='http://127.0.0.1:8008/test', headers=headers).json()
        self.assertEqual(data['trace_info']['client']['ip'], '1.2.3.4')
        self.assertEqual(data['trace_info']['client']['phone'], '09123456789')
