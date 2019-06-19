# From https://github.com/grpc/grpc/blob/v1.9.1/src/python/grpcio_testing/grpc_testing/_server/_servicer_context.py

import time
import grpc

class RabbitMQServicerContext(grpc.ServicerContext):
    class Finished(Exception):
        pass

    def __init__(self, timeout):
        self._deadline = time.time() + timeout if timeout else None
        self._code = None
        self._details = None

    def is_active(self):
        return True

    def time_remaining(self):
        if self._deadline is None:
            return None
        else:
            return max(0.0, self._deadline - time.time())

    def cancel(self):
        raise NotImplementedError()

    def add_callback(self, callback):
        raise NotImplementedError()

    def invocation_metadata(self):
        return None

    def peer(self):
        raise NotImplementedError()

    def peer_identities(self):
        raise NotImplementedError()

    def peer_identity_key(self):
        raise NotImplementedError()

    def auth_context(self):
        raise NotImplementedError()

    def send_initial_metadata(self, initial_metadata):
        pass

    def set_trailing_metadata(self, trailing_metadata):
        pass

    def abort(self, code, details):
        self._code = code
        self._details = details
        raise RabbitMQServicerContext.Finished()

    def abort_with_status(self, status):
        raise NotImplementedError()

    def set_code(self, code):
        self._code = code

    def set_details(self, details):
        self._details = details

    def get_code(self):
        return self._code
