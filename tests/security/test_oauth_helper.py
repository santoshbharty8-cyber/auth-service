import json
from unittest.mock import Mock

from app.security.oauth_helper import OAuthHelper


def test_generate_state():
    state = OAuthHelper.generate_state()
    assert isinstance(state, str)
    assert len(state) > 0


def test_generate_pkce():
    verifier, challenge = OAuthHelper.generate_pkce()
    assert isinstance(verifier, str)
    assert isinstance(challenge, str)
    assert len(verifier) > 0
    assert len(challenge) > 0


def test_store_state():
    redis_mock = Mock()
    state = "test_state"
    data = {"key": "value"}
    OAuthHelper.store_state(redis_mock, state, data)
    redis_mock.setex.assert_called_once_with(
        f"{OAuthHelper.PREFIX}{state}",
        OAuthHelper.TTL,
        json.dumps(data)
    )


def test_consume_state_found():
    redis_mock = Mock()
    state = "test_state"
    data = {"key": "value"}
    redis_mock.get.return_value = json.dumps(data)
    result = OAuthHelper.consume_state(redis_mock, state)
    assert result == data
    redis_mock.get.assert_called_once_with(f"{OAuthHelper.PREFIX}{state}")
    redis_mock.delete.assert_called_once_with(f"{OAuthHelper.PREFIX}{state}")


def test_consume_state_not_found():
    redis_mock = Mock()
    redis_mock.get.return_value = None
    result = OAuthHelper.consume_state(redis_mock, "missing")
    assert result is None
    redis_mock.delete.assert_not_called()