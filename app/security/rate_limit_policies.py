# ENDPOINT_LIMITS = {
#     "/auth/login": ("login", 5, 60),
#     "/auth/register": ("register", 3, 60),
#     "/auth/refresh": ("refresh", 20, 60),
#     "/audit-logs": ("admin", 50, 60),
# }
ENDPOINT_LIMITS = {
    "/auth/login": ("login", 3, 60),
    "/auth/register": ("register", 100, 60),
    "/auth/refresh": ("refresh", 20, 60),
    "/audit-logs": ("admin", 50, 60),
    "/auth/request-otp": ("otp_request", 3, 60),
    "/auth/login-otp": ("otp_verify", 5, 60),
}
