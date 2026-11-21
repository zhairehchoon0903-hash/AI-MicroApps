"""Small, testable authentication policy for the Film Studio API."""
import hmac

LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}


def api_auth_failure(configured_host: str, api_token: str, supplied_authorization: str):
    """Return (HTTP status, detail) when access must be rejected, otherwise None.

    The server's bind address is the network boundary. Codespaces port forwarding
    proxies requests, so request.client.host is not a reliable indicator of whether
    the application itself is publicly bound. A non-loopback bind always requires
    a configured bearer token; a configured token is always enforced.
    """
    remote_binding = configured_host not in LOOPBACK_HOSTS
    if remote_binding and not api_token:
        return (503, "Remote API access is disabled until FILM_STUDIO_TOKEN is configured.")
    if api_token and not hmac.compare_digest(supplied_authorization, f"Bearer {api_token}"):
        return (401, "A valid Film Studio access token is required.")
    return None
