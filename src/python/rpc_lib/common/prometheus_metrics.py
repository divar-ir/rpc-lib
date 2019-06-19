import prometheus_client

SERVER_LATENCY = prometheus_client.Histogram(
        'rpc_server_latency_histogram', 'Overall latency after all retries', [
            'service_name', 'method', 'server_type'])
SERVER_STATUS_CODE = prometheus_client.Counter(
        'rpc_server_status_code', 'Server side status code', ['service_name', 'method', 'status_code', 'server_type'])
SERVER_IN_PROGRESS = prometheus_client.Gauge("rpc_server_inprogress_requests", "", ["service_name", "server_type"], multiprocess_mode='livesum')
SERVER_FREE_WORKERS = prometheus_client.Gauge("rpc_server_free_workers", "", ["service_name", "server_type"], multiprocess_mode='livesum')

CLIENT_IN_PROGRESS_REQUESTS = prometheus_client.Gauge(
    "rpc_client_in_progress_requests",
    "Client side in progress requests",
    ["client_service_name", "server_service_name", "method_name"],
    multiprocess_mode='livesum'
)

CLIENT_ATTEMPT_DEADLINE = prometheus_client.Histogram(
        'rpc_deadline_histogram', 'Deadline set for each attempt', [
            'caller_service_name', 'service_name', 'config', 'method'])
CLIENT_ATTEMPT_LATENCY = prometheus_client.Summary(
        'rpc_attempt_latency_summary', 'Latency for each attempt', [
            'caller_service_name', 'service_name', 'config', 'method', 'status_code'])
CLIENT_LATENCY = prometheus_client.Histogram(
        'rpc_latency_histogram', 'Overall latency after all retries', [
            'caller_service_name', 'service_name', 'method'])

CLIENT_RETRIES = prometheus_client.Summary(
        'rpc_retries_summary', 'Number of retries', [
            'caller_service_name', 'service_name', 'method', 'status_code'])

JOB_LATENCY = prometheus_client.Histogram(
        'rpc_server_job_latency', 'Overall latency of async RabbitMQ calls', [
        'caller_service_name', 'service_name', 'method', 'status_code'])

JOB_RETRIES = prometheus_client.Summary('rpc_server_job_retries', 'number of retries to execute a job', [
        'caller_service_name', 'service_name', 'method', 'status_code' ])
