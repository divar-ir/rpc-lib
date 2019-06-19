import threading

from rpc_lib.common.context_holder.base import BaseContextHolder


class ThreadContextHolder(BaseContextHolder):
    def __init__(self):
        self._context_holder = None

    def context_holder(self):
        if self._context_holder is None:
            self._context_holder = threading.local()
        return self._context_holder
