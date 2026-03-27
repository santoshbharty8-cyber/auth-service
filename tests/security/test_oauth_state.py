import pytest
from unittest.mock import Mock, patch

from app.security.oauth_state import create_oauth_state, validate_oauth_state


@patch('app.security.oauth_state.redis_client')
def test_create_oauth_state_generates_and_stores(mock_redis):
    mock_redis.setex = Mock()

    state = create_oauth_state()

    assert isinstance(state, str)
    assert len(state) > 0
    mock_redis.setex.assert_called_once()
    call_args = mock_redis.setex.call_args
    assert call_args[0][0].startswith('oauth_state:')
    assert call_args[0][1] == 300
    assert call_args[0][2] == "1"


@patch('app.security.oauth_state.redis_client')
def test_validate_oauth_state_valid(mock_redis):
    mock_redis.get.return_value = "1"
    mock_redis.delete = Mock()

    result = validate_oauth_state("valid_state")

    assert result is True
    mock_redis.get.assert_called_once_with("oauth_state:valid_state")
    mock_redis.delete.assert_called_once_with("oauth_state:valid_state")


@patch('app.security.oauth_state.redis_client')
def test_validate_oauth_state_invalid(mock_redis):
    mock_redis.get.return_value = None
    mock_redis.delete = Mock()

    result = validate_oauth_state("invalid_state")

    assert result is False
    mock_redis.get.assert_called_once_with("oauth_state:invalid_state")
    mock_redis.delete.assert_not_called()