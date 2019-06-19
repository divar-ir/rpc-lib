from rpc_lib.common import servicer
from rpc_lib.common.prometheus_metrics import SERVER_IN_PROGRESS, SERVER_FREE_WORKERS
from rpc_lib.django.django_task_context import DjangoTaskContext

try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    class MiddlewareMixin(object):
        pass


class ContextMiddleware(MiddlewareMixin):
    def process_request(self, request):
        SERVER_FREE_WORKERS.labels(servicer.name(), 'django').dec()
        SERVER_IN_PROGRESS.labels(servicer.name(), 'django').inc()
        request.counted_request = True
        servicer.set_current_context(DjangoTaskContext())

    def process_response(self, request, response):
        if getattr(request, 'counted_request', False):
            SERVER_FREE_WORKERS.labels(servicer.name(), 'django').inc()
            SERVER_IN_PROGRESS.labels(servicer.name(), 'django').dec()
            request.counted_request = False
        return response

    def process_exception(self, request, exception):
        if getattr(request, 'counted_request', False):
            SERVER_FREE_WORKERS.labels(servicer.name(), 'django').inc()
            SERVER_IN_PROGRESS.labels(servicer.name(), 'django').dec()
            request.counted_request = False



