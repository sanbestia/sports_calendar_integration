import pytest
import os
from unittest.mock import patch, MagicMock, mock_open
from google.auth.exceptions import RefreshError
from functions.check_calendar_tokens import check_calendar_tokens


def make_valid_creds() -> MagicMock:
    creds = MagicMock()
    creds.valid = True
    creds.expired = False
    creds.refresh_token = None
    return creds


def make_expired_creds() -> MagicMock:
    creds = MagicMock()
    creds.valid = False
    creds.expired = True
    creds.refresh_token = "some_refresh_token"
    return creds


# --- Tests ---

def test_returns_valid_creds_when_token_exists():
    """Returns credentials directly when token file exists and is valid."""
    mock_creds = make_valid_creds()

    with patch("functions.check_calendar_tokens.os.path.exists", return_value=True), \
         patch("functions.check_calendar_tokens.Credentials.from_authorized_user_file", return_value=mock_creds):

        result = check_calendar_tokens()

    assert result == mock_creds


def test_refreshes_creds_when_expired():
    """Refreshes credentials when token exists but is expired."""
    mock_creds = make_expired_creds()

    with patch("functions.check_calendar_tokens.os.path.exists", return_value=True), \
         patch("functions.check_calendar_tokens.Credentials.from_authorized_user_file", return_value=mock_creds), \
         patch("functions.check_calendar_tokens.Request"), \
         patch("builtins.open", mock_open()):

        result = check_calendar_tokens()

    mock_creds.refresh.assert_called_once()


def test_deletes_token_and_runs_flow_when_refresh_fails():
    """Deletes token file and runs auth flow when refresh raises an exception."""
    mock_creds = make_expired_creds()
    mock_creds.refresh.side_effect = RefreshError("Refresh failed")
    mock_flow_creds = make_valid_creds()

    mock_flow = MagicMock()
    mock_flow.run_local_server.return_value = mock_flow_creds

    with patch("functions.check_calendar_tokens.os.path.exists", return_value=True), \
         patch("functions.check_calendar_tokens.Credentials.from_authorized_user_file", return_value=mock_creds), \
         patch("functions.check_calendar_tokens.Request"), \
         patch("functions.check_calendar_tokens.os.remove") as mock_remove, \
         patch("functions.check_calendar_tokens.InstalledAppFlow.from_client_secrets_file", return_value=mock_flow), \
         patch("builtins.open", mock_open()):

        result = check_calendar_tokens()

    mock_remove.assert_called_once_with("token.json")
    mock_flow.run_local_server.assert_called_once()
    assert result == mock_flow_creds


def test_runs_auth_flow_when_no_token_file():
    """Runs auth flow when no token file exists."""
    mock_flow_creds = make_valid_creds()

    mock_flow = MagicMock()
    mock_flow.run_local_server.return_value = mock_flow_creds

    with patch("functions.check_calendar_tokens.os.path.exists", return_value=False), \
         patch("functions.check_calendar_tokens.InstalledAppFlow.from_client_secrets_file", return_value=mock_flow), \
         patch("builtins.open", mock_open()):

        result = check_calendar_tokens()

    mock_flow.run_local_server.assert_called_once()
    assert result == mock_flow_creds


def test_saves_token_file_after_auth_flow():
    """Writes credentials to token.json after a successful auth flow."""
    mock_flow_creds = make_valid_creds()
    mock_flow_creds.to_json.return_value = '{"token": "abc"}'

    mock_flow = MagicMock()
    mock_flow.run_local_server.return_value = mock_flow_creds

    with patch("functions.check_calendar_tokens.os.path.exists", return_value=False), \
         patch("functions.check_calendar_tokens.InstalledAppFlow.from_client_secrets_file", return_value=mock_flow), \
         patch("builtins.open", mock_open()) as mock_file:

        check_calendar_tokens()

    mock_file.assert_called_once_with("token.json", "w")


def test_non_refresh_error_propagates():
    """Non-RefreshError exceptions from token refresh are not caught."""
    mock_creds = make_expired_creds()
    mock_creds.refresh.side_effect = OSError("Network error")

    with patch("functions.check_calendar_tokens.os.path.exists", return_value=True), \
         patch("functions.check_calendar_tokens.Credentials.from_authorized_user_file", return_value=mock_creds), \
         patch("functions.check_calendar_tokens.Request"):
        with pytest.raises(OSError):
            check_calendar_tokens()
