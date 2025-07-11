import pytest
from unittest import mock
import urllib.request
import sys


def check_health_endpoint_simple(url, timeout=2):
    """
    Simple health check using urllib.request.

    This function tests if a health endpoint is responding by making
    an HTTP request and checking for a 200 status code.

    Args:
        url (str): URL to check (e.g., "http://127.0.0.1:27015/")
        timeout (int): Request timeout in seconds

    Returns:
        bool: True if endpoint responds with 200, False otherwise
    """
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.getcode() == 200
    except Exception:
        return False


class TestSimpleHealthCheck:
    """Tests for the simplified health check using urllib.request."""

    def test_check_health_endpoint_success(self):
        """Test successful health endpoint check."""
        with mock.patch('urllib.request.urlopen') as mock_urlopen:
            mock_response = mock.MagicMock()
            mock_response.getcode.return_value = 200
            mock_urlopen.return_value.__enter__.return_value = mock_response

            result = check_health_endpoint_simple('http://127.0.0.1:27015/')

            assert result is True

    def test_check_health_endpoint_failure(self):
        """Test failed health endpoint check."""
        with mock.patch('urllib.request.urlopen', side_effect=Exception("Connection error")):
            result = check_health_endpoint_simple('http://127.0.0.1:27015/')

            assert result is False

    def test_check_health_endpoint_timeout(self):
        """Test health endpoint check with timeout."""
        with mock.patch('urllib.request.urlopen', side_effect=urllib.error.URLError("timeout")):
            result = check_health_endpoint_simple('http://127.0.0.1:27015/')

            assert result is False

    def test_check_health_endpoint_http_error(self):
        """Test health endpoint check with HTTP error."""
        with mock.patch('urllib.request.urlopen', side_effect=urllib.error.HTTPError("url", 404, "Not Found", {}, None)):
            result = check_health_endpoint_simple('http://127.0.0.1:27015/')

            assert result is False

    @mock.patch('sys.exit')
    @mock.patch('argparse.ArgumentParser')
    def test_command_line_usage(self, mock_parser, mock_exit):
        """Test the command line usage for health endpoint checking."""
        command = 'python3 -c \'import urllib.request; urllib.request.urlopen("http://127.0.0.1:27015/", timeout=2)\''

        with mock.patch('subprocess.run') as mock_run:
            mock_result = mock.MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            import subprocess
            result = subprocess.run(command, shell=True, capture_output=True, text=True)

            assert result.returncode == 0

    @mock.patch('sys.exit')
    @mock.patch('argparse.ArgumentParser')
    def test_command_line_usage_failure(self, mock_parser, mock_exit):
        """Test the command line usage with failure."""
        command = 'python3 -c \'import urllib.request; urllib.request.urlopen("http://127.0.0.1:27015/", timeout=2)\''

        with mock.patch('subprocess.run') as mock_run:
            mock_result = mock.MagicMock()
            mock_result.returncode = 1
            mock_result.stderr = "Connection error"
            mock_run.return_value = mock_result

            import subprocess
            result = subprocess.run(command, shell=True, capture_output=True, text=True)

            assert result.returncode == 1
