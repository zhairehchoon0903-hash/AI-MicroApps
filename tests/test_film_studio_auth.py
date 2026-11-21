import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "film-studio"))

from auth_guard import api_auth_failure


def test_loopback_binding_allows_authenticated_port_forward_proxy_without_token():
    assert api_auth_failure("127.0.0.1", "", "") is None


def test_public_binding_without_token_is_disabled():
    result = api_auth_failure("0.0.0.0", "", "")
    assert result[0] == 503


def test_configured_token_is_required_even_on_loopback():
    result = api_auth_failure("127.0.0.1", "secret", "")
    assert result[0] == 401


def test_correct_bearer_token_is_accepted_on_public_binding():
    assert api_auth_failure("0.0.0.0", "secret", "Bearer secret") is None


def test_incorrect_bearer_token_is_rejected():
    result = api_auth_failure("0.0.0.0", "secret", "Bearer wrong")
    assert result[0] == 401
