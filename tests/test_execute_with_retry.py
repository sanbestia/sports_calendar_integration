import pytest
from unittest.mock import MagicMock, patch
from googleapiclient.errors import HttpError
from functions.calendar_methods import _execute_with_retry, _MAX_RETRIES


def make_request(return_value=None, side_effect=None) -> MagicMock:
    """Helper to create a fake Google API request object."""
    mock = MagicMock()
    if side_effect is not None:
        mock.execute.side_effect = side_effect
    else:
        mock.execute.return_value = return_value
    return mock


def make_http_error(status: int) -> HttpError:
    resp = MagicMock()
    resp.status = status
    resp.status_code = status
    return HttpError(resp=resp, content=b"error")


@patch("functions.calendar_methods.time.sleep")
def test_returns_result_on_first_try(mock_sleep):
    """Returns the result directly when execute succeeds."""
    request = make_request(return_value={"id": "abc"})
    result = _execute_with_retry(request)
    assert result == {"id": "abc"}
    request.execute.assert_called_once()
    mock_sleep.assert_not_called()


@patch("functions.calendar_methods.time.sleep")
def test_retries_on_429(mock_sleep):
    """Retries on rate limit and returns result on eventual success."""
    error = make_http_error(429)
    request = make_request(side_effect=[error, error, {"id": "abc"}])
    result = _execute_with_retry(request)
    assert result == {"id": "abc"}
    assert request.execute.call_count == 3
    assert mock_sleep.call_count == 2


@patch("functions.calendar_methods.time.sleep")
def test_retries_on_503(mock_sleep):
    """Retries on 503 Service Unavailable."""
    error = make_http_error(503)
    request = make_request(side_effect=[error, {"id": "abc"}])
    result = _execute_with_retry(request)
    assert result == {"id": "abc"}
    assert request.execute.call_count == 2
    assert mock_sleep.call_count == 1


@patch("functions.calendar_methods.time.sleep")
def test_raises_after_max_retries(mock_sleep):
    """Raises HttpError after exhausting all retries."""
    error = make_http_error(500)
    request = make_request(side_effect=error)
    with pytest.raises(HttpError):
        _execute_with_retry(request)
    assert request.execute.call_count == _MAX_RETRIES


@patch("functions.calendar_methods.time.sleep")
def test_raises_immediately_on_non_retryable_http_error(mock_sleep):
    """Does not retry on 403 Forbidden — not a transient error."""
    error = make_http_error(403)
    request = make_request(side_effect=error)
    with pytest.raises(HttpError):
        _execute_with_retry(request)
    request.execute.assert_called_once()
    mock_sleep.assert_not_called()


@patch("functions.calendar_methods.time.sleep")
def test_raises_on_broken_pipe_immediately(mock_sleep):
    """Propagates BrokenPipeError without retrying — reconnection is the caller's responsibility."""
    request = make_request(side_effect=BrokenPipeError)
    with pytest.raises(BrokenPipeError):
        _execute_with_retry(request)
    request.execute.assert_called_once()
    mock_sleep.assert_not_called()


@patch("functions.calendar_methods.time.sleep")
def test_raises_on_generic_exception(mock_sleep):
    """Propagates arbitrary exceptions immediately."""
    request = make_request(side_effect=ValueError("unexpected"))
    with pytest.raises(ValueError):
        _execute_with_retry(request)
    request.execute.assert_called_once()
    mock_sleep.assert_not_called()
