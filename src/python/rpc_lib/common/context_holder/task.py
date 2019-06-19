import asyncio

from rpc_lib.common.context_holder.base import BaseContextHolder


class TaskContextHolder(BaseContextHolder):
    def __init__(self, event_loop):
        self._event_loop = event_loop

    def context_holder(self):
        return asyncio.Task.current_task(loop=self._event_loop)
