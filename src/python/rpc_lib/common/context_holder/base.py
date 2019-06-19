class BaseContextHolder(object):
    def current_context(self):
        if not hasattr(self.context_holder(), 'current'):
            return None
        return self.context_holder().current

    def set_current_context(self, context):
        self.context_holder().current = context
