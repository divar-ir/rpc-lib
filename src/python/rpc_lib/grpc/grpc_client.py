import grpc
from rpc_lib.grpc.interceptors import flags, retry, timeout


class GrpcClient(object):
    def __init__(self, server_address):
        self._channel = grpc.insecure_channel(
            server_address,
            options=[('grpc.lb_policy_name', 'round_robin')])

    def get_stub(self, stub_factory, remote_service_name, instance_name):
        channel = grpc.intercept_channel(
            self._channel,
            flags.flags_interceptor(),
            retry.RetryInterceptor(remote_service_name),
            timeout.TimeoutInterceptor(remote_service_name, instance_name))

        return stub_factory(channel)
