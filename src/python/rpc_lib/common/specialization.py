class RpcLibSpecialization(object):
    def create_state_proto(self):
        raise NotImplementedError();

    # returns pair config_map_namespace, config_map_name
    def kuber_global_config(self):
        raise NotImplementedError();

# Must be overriden by product
_specialization = RpcLibSpecialization()

def set_specialization(specialization):
    global _specialization
    _specialization = specialization

def create_state_proto():
    return _specialization.create_state_proto()

def get_kuber_global_config():
    return _specialization.kuber_global_config()
