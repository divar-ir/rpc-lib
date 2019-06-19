from rpc_lib.common import servicer

class RequestWithContext():
    def __init__(self, request):
        self.request = request
        self.context = servicer.current_context()

def extract_request_and_context(request_obj):
    if request_obj and issubclass(type(request_obj), RequestWithContext):
        return request_obj.request, request_obj.context
    else:
        return request_obj, servicer.current_context()


