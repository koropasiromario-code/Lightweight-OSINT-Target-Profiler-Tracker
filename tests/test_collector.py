import socket
from unittest.mock import patch

import pytest

from collector import TargetValidationError, validate_target


def test_rejects_http():
    with pytest.raises(TargetValidationError):
        validate_target("http://example.com")


def test_rejects_credentials():
    with pytest.raises(TargetValidationError):
        validate_target("https://user:pass@example.com")


def test_rejects_non_allowlisted_host():
    with pytest.raises(TargetValidationError):
        validate_target("https://not-allowed.invalid")


def test_rejects_nonstandard_port():
    with pytest.raises(TargetValidationError):
        validate_target("https://example.com:8443")


@patch("collector.socket.getaddrinfo")
def test_rejects_private_dns_result(mock_getaddrinfo):
    mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]
    with pytest.raises(TargetValidationError, match="nonpublik"):
        validate_target("https://example.com")


@patch("collector.socket.getaddrinfo")
def test_normalizes_allowed_url_and_drops_fragment(mock_getaddrinfo):
    mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
    assert validate_target("https://EXAMPLE.com/path#fragment") == "https://example.com/path"
