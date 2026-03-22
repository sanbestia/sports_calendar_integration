import pytest
from unittest.mock import MagicMock
from googleapiclient.errors import HttpError
from functions.calendar_methods import _execute_with_retry


def make_request(return_value=None, side_effect=None) -> MagicMock:
    """Helper to create a fake Google API request object."""
    mock = MagicMock()
    if side_effect is not None:
        mock.execute.side_effect = side_effect
    else:
        mock.execute.return_value = return_value
    return mock


def test_returns_result_on_first_try():
    """Returns the result directly when execute succeeds."""
    request = make_request(return_value={"id": "abc"})
    result = _execute_with_retry(request)
    assert result == {"id": "abc"}
    request.execute.assert_called_once()


def test_raises_broken_pipe_immediately():
    """Propagates BrokenPipeError without retrying — reconnection is the caller's responsibility."""
    request = make_request(side_effect=BrokenPipeError)
    with pytest.raises(BrokenPipeError):
        _execute_with_retry(request)
    request.execute.assert_called_once()


def test_raises_on_http_error():
    """Propagates HttpError immediately."""
    http_error = HttpError(resp=MagicMock(status=403), content=b"Forbidden")
    request = make_request(side_effect=http_error)
    with pytest.raises(HttpError):
        _execute_with_retry(request)
    request.execute.assert_called_once()


def test_raises_on_generic_exception():
    """Propagates arbitrary exceptions immediately."""
    request = make_request(side_effect=ValueError("unexpected"))
    with pytest.raises(ValueError):
        _execute_with_retry(request)
    request.execute.assert_called_once()
