"""
Utility functions for the RUSH application.
"""


def get_client_ip(group, request):
    """
    Get the real client IP address from the request, accounting for reverse proxies.

    Checks X-Forwarded-For and X-Real-IP headers that are set by Nginx proxy.
    Falls back to REMOTE_ADDR if no proxy headers are present.

    Args:
        request: Django HttpRequest object

    Returns:
        str: Client IP address
    """
    # Check X-Forwarded-For header (set by Nginx)
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        # X-Forwarded-For can contain multiple IPs (client, proxy1, proxy2, ...)
        # The first one is the original client IP
        ip = x_forwarded_for.split(",")[0].strip()
        return ip

    # Check X-Real-IP header (also set by Nginx)
    x_real_ip = request.META.get("HTTP_X_REAL_IP")
    if x_real_ip:
        return x_real_ip.strip()

    # Fall back to REMOTE_ADDR (direct connection, no proxy)
    return request.META.get("REMOTE_ADDR", "")


import logging
import time
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@contextmanager
def log_execution_time(operation_name: str, log_level: int = logging.INFO):
    """
    Context manager that logs the time spent executing a block of code.

    Args:
        operation_name: Description of the operation being timed
        log_level: Logging level (default: logging.INFO)

    Usage:
        with log_execution_time("Database query"):
            # Your code here
            results = expensive_query()
    """
    start_time = time.time()
    try:
        yield
    finally:
        elapsed_time = time.time() - start_time
        logger.log(log_level, f"{operation_name} took {elapsed_time:.3f} seconds")


@contextmanager
def log_execution_time_with_result(operation_name: str, log_level: int = logging.INFO):
    """
    Context manager that logs execution time and provides a way to log additional result info.

    Usage:
        with log_execution_time_with_result("Database query") as timer:
            results = expensive_query()
            timer['count'] = len(results)  # Optional: add context to the log
    """
    start_time = time.time()
    context = {}
    try:
        yield context
    finally:
        elapsed_time = time.time() - start_time
        extra_info = f" ({context})" if context else ""
        logger.log(log_level, f"{operation_name} took {elapsed_time:.3f} seconds{extra_info}")
