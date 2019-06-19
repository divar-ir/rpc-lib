# Changed from src/python/grpcio/grpc/_interceptor.py in grpc repo.

import grpc

class FailureOutcome(grpc.RpcError, grpc.Future, grpc.Call):
    def __init__(self, code, details):
        super(FailureOutcome, self).__init__()
        self._code = code
        self._details = details

    def initial_metadata(self):
        return None

    def trailing_metadata(self):
        return None

    def code(self):
        return self._code

    def details(self):
        return self._details

    def cancel(self):
        return False

    def cancelled(self):
        return False

    def is_active(self):
        return False

    def time_remaining(self):
        return None

    def running(self):
        return False

    def done(self):
        return True

    def result(self, ignored_timeout=None):
        raise self

    def exception(self, ignored_timeout=None):
        return self

    def traceback(self, ignored_timeout=None):
        return None

    def add_callback(self, callback):
        return False

    def add_done_callback(self, fn):
        fn(self)

    def __iter__(self):
        return self

    def __next__(self):
        raise self._exception

    def next(self):
        return self.__next__()
