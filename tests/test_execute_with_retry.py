import pytest
from unittest.mock import MagicMock, patch, call
from googleapiclient.errors import HttpError
from functions.calendar_methods import _execute_with_retry, _RETRY_DELAY_SECONDS


def make_request(return_value=None, side_effect=None) -> MagicMock:
    """Helper to create a fake Google API request object."""
    mock = MagicMock()
    if side_effect is not None:
        mock.execute.side_effect = side_effect
    else:
        mock.execute.return_value = return_value
    return mock


# --- Success cases ---

def test_returns_result_on_first_try():
    """Returns the result directly when the first execute succeeds."""
    request = make_request(return_value={"id": "abc"})
    result = _execute_with_retry(request)
    assert result == {"id": "abc"}
    request.execute.assert_called_once()


def test_does_not_sleep_on_success():
    """Does not call time.sleep when the first attempt succeeds."""
    request = make_request(return_value={"id": "abc"})
    with patch("functions.calendar_methods.time.sleep") as mock_sleep:
        _execute_with_retry(request)
    mock_sleep.assert_not_called()


# --- Retry cases ---

def test_retries_on_broken_pipe_and_succeeds():
    """Retries once when BrokenPipeError is raised and returns the result."""
    request = make_request(side_effect=[BrokenPipeError, {"id": "abc"}])
    result = _execute_with_retry(request)
    assert result == {"id": "abc"}
    assert request.execute.call_count == 2


def test_sleeps_before_retry():
    """Sleeps for the configured delay before retrying."""
    request = make_request(side_effect=[BrokenPipeError, {"id": "abc"}])
    with patch("functions.calendar_methods.time.sleep") as mock_sleep:
        _execute_with_retry(request)
    mock_sleep.assert_called_once_with(_RETRY_DELAY_SECONDS)


def test_sleep_happens_before_second_execute():
    """Ensures sleep is called before the retry, not after."""
    call_order = []
    request = MagicMock()

    def tracked_execute():
        call_order.append("execute")
        if len(call_order) == 1:
            raise BrokenPipeError
        return {"id": "abc"}

    request.execute.side_effect = tracked_execute

    with patch("functions.calendar_methods.time.sleep", side_effect=lambda _: call_order.append("sleep")):
        _execute_with_retry(request)

    assert call_order == ["execute", "sleep", "execute"]


# --- Failure cases ---

def test_raises_if_retry_also_fails():
    """Propagates BrokenPipeError if the retry also fails."""
    request = make_request(side_effect=[BrokenPipeError, BrokenPipeError])
    with patch("functions.calendar_methods.time.sleep"):
        with pytest.raises(BrokenPipeError):
            _execute_with_retry(request)
    assert request.execute.call_count == 2


def test_does_not_retry_on_http_error():
    """Does not retry when an HttpError is raised — propagates immediately."""
    http_error = HttpError(resp=MagicMock(status=403), content=b"Forbidden")
    request = make_request(side_effect=http_error)
    with patch("functions.calendar_methods.time.sleep") as mock_sleep:
        with pytest.raises(HttpError):
            _execute_with_retry(request)
    request.execute.assert_called_once()
    mock_sleep.assert_not_called()


def test_does_not_retry_on_generic_exception():
    """Does not retry on arbitrary exceptions — propagates immediately."""
    request = make_request(side_effect=ValueError("unexpected"))
    with patch("functions.calendar_methods.time.sleep") as mock_sleep:
        with pytest.raises(ValueError):
            _execute_with_retry(request)
    request.execute.assert_called_once()
    mock_sleep.assert_not_called()