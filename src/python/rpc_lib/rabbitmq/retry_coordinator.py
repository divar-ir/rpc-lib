import grpc

def linear_backoff(start=5, step=3):
    def generator(retry_cnt):
        return start + retry_cnt * step

    return generator


class RetryCoordinator():
    max_retries_by_code = {
        grpc.StatusCode.INTERNAL: 3,
        grpc.StatusCode.ABORTED: 3,
        grpc.StatusCode.UNAVAILABLE: 3,
    }

    def max_retries(self, rpc_info, status_code):
        return RetryCoordinator.max_retries_by_code.get(status_code, 0)

    def backoff(self, rpc_info, status_code, retry_cnt):
        return linear_backoff()(retry_cnt)
