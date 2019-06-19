import collections
import grpc

class _ClientCallDetails(
        collections.namedtuple(
            '_ClientCallDetails',
            ('method', 'timeout', 'metadata', 'credentials', 'wait_for_ready')),
        grpc.ClientCallDetails):
    pass

def create(method, timeout, metadata, credentials, wait_for_ready):
    return _ClientCallDetails(method, timeout, metadata, credentials, wait_for_ready)
