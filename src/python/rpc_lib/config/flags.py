from rpc_lib.config import flags_pb2
from rpc_lib.config.flags_manager import FlagsManager
from rpc_lib.config.modules import modules

modules.register_flags_manager(FlagsManager())
FLAGS = modules.flags_manager.flags_holder

def DEFINE_BOOL_FLAG(name, base_value=False, overrides=None):
    return modules.flags_manager.register_flag(name, flags_pb2.BOOLEAN, base_value, overrides)

def DEFINE_INTEGER_FLAG(name, base_value=0, overrides=None):
    return modules.flags_manager.register_flag(name, flags_pb2.INTEGER, base_value, overrides)

def DEFINE_FLOAT_FLAG(name, base_value=0, overrides=None):
    return modules.flags_manager.register_flag(name, flags_pb2.FLOAT, base_value, overrides)

def DEFINE_STRING_FLAG(name, base_value='', overrides=None):
    return modules.flags_manager.register_flag(name, flags_pb2.STRING, base_value, overrides)
