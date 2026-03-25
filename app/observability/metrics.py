from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["endpoint"],
)

RATE_LIMIT_EXCEEDED = Counter(
    "rate_limit_exceeded_total",
    "Total number of rate limit violations",
    ["type", "endpoint"],
)

RATE_LIMIT_ERRORS = Counter(
    "rate_limiter_errors_total",
    "Total errors in the rate limiter",
)