class GlobalConfigModules():
    def __init__(self):
        self._flags_manager = None
        self._services_manager = None
        self._global_config_wrapper = None
        self._conditions_manager = None

    def register_flags_manager(self, flags_manager):
        self._flags_manager = flags_manager

    def register_services_manager(self, services_manager):
        self._services_manager = services_manager

    def register_global_config_wrapper(self, global_config_wrapper):
        self._global_config_wrapper = global_config_wrapper

    def remove_global_config_wrapper(self):
        self._global_config_wrapper = None

    def register_conditions_manager(self, conditions_manager):
        self._conditions_manager = conditions_manager

    @property
    def flags_manager(self):
        return self._flags_manager

    @property
    def services_manager(self):
        return self._services_manager

    @property
    def global_config_wrapper(self):
        return self._global_config_wrapper

    @property
    def conditions_manager(self):
        return self._conditions_manager

modules = GlobalConfigModules()
