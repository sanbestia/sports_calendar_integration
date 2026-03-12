import pytest
from functions.utils import sanitize_for_log


# --- ANSI escape codes ---

def test_strips_ansi_color_codes():
    """Removes ANSI color escape sequences."""
    assert sanitize_for_log("\x1b[31mRed Text\x1b[0m") == "Red Text"


def test_strips_ansi_bold():
    """Removes ANSI bold escape sequence."""
    assert sanitize_for_log("\x1b[1mBold\x1b[0m") == "Bold"


def test_strips_ansi_multi_param():
    """Removes ANSI sequences with multiple parameters."""
    assert sanitize_for_log("\x1b[1;32mGreen Bold\x1b[0m") == "Green Bold"


def test_strips_ansi_cursor_movement():
    """Removes ANSI cursor movement sequences."""
    assert sanitize_for_log("\x1b[2Amove up") == "move up"


# --- Newlines and carriage returns ---

def test_replaces_newline_with_space():
    """Replaces newline characters with a space."""
    assert sanitize_for_log("line one\nline two") == "line one line two"


def test_replaces_carriage_return_with_space():
    """Replaces carriage return characters with a space."""
    assert sanitize_for_log("line one\rline two") == "line one line two"


def test_replaces_crlf_with_spaces():
    """Replaces Windows-style CRLF with spaces."""
    assert sanitize_for_log("line one\r\nline two") == "line one  line two"


def test_strips_leading_and_trailing_whitespace():
    """Strips surrounding whitespace after substitutions."""
    assert sanitize_for_log("  hello  ") == "hello"


def test_strips_leading_newline():
    """Strips a leading newline that becomes a leading space after substitution."""
    assert sanitize_for_log("\nhello") == "hello"


# --- Combined cases ---

def test_strips_ansi_and_normalises_newlines():
    """Handles a string with both ANSI codes and newlines."""
    assert sanitize_for_log("\x1b[31mError\x1b[0m\ndetail") == "Error detail"


def test_handles_injected_fake_log_line():
    """Prevents a malicious string from injecting a fake log entry."""
    malicious = "Real Team\nINFO - Fake log entry injected by attacker"
    result = sanitize_for_log(malicious)
    assert "\n" not in result
    assert result == "Real Team INFO - Fake log entry injected by attacker"


# --- Clean strings ---

def test_clean_string_passes_through_unchanged():
    """A normal string with no special characters is returned as-is."""
    assert sanitize_for_log("Carlos Alcaraz") == "Carlos Alcaraz"


def test_empty_string_returns_empty():
    """An empty string returns an empty string."""
    assert sanitize_for_log("") == ""


def test_string_with_unicode_passes_through():
    """Unicode characters in team names are preserved."""
    assert sanitize_for_log("Atlético de Madrid") == "Atlético de Madrid"