import pytest
from unittest import mock

from neurons.Validator.health_check_server import (
    HealthCheckHandler,
    TimeoutHTTPServer
)


# ============================================================================
# TESTS FOR HEALTH CHECK SERVER (HTTP Server Component)
# ============================================================================

class TestHealthCheckServer:
    """Tests for the health check HTTP server component."""

    def test_health_check_handler_get_root(self):
        """Test that GET / returns 200 OK."""
        handler = mock.MagicMock()
        handler.path = '/'
        handler.send_response = mock.MagicMock()
        handler.send_header = mock.MagicMock()
        handler.end_headers = mock.MagicMock()
        handler.wfile = mock.MagicMock()

        HealthCheckHandler.do_GET(handler)

        handler.send_response.assert_called_with(200)
        handler.send_header.assert_called_with('Content-Type', 'text/plain')
        handler.end_headers.assert_called_once()
        handler.wfile.write.assert_called_with(b"Health OK")


    def test_health_check_handler_404(self):
        """Test that invalid paths return 404."""
        handler = mock.MagicMock()
        handler.path = '/invalid'
        handler.send_response = mock.MagicMock()
        handler.send_header = mock.MagicMock()
        handler.end_headers = mock.MagicMock()
        handler.wfile = mock.MagicMock()

        HealthCheckHandler.do_GET(handler)

        handler.send_response.assert_called_with(404)
        handler.wfile.write.assert_called_with(b"Not Found")

    def test_health_check_handler_head_root(self):
        """Test that HEAD / returns 200 OK."""
        handler = mock.MagicMock()
        handler.path = '/'
        handler.send_response = mock.MagicMock()
        handler.send_header = mock.MagicMock()
        handler.end_headers = mock.MagicMock()

        HealthCheckHandler.do_HEAD(handler)

        handler.send_response.assert_called_with(200)
        handler.send_header.assert_called_with('Content-Type', 'text/plain')
        handler.end_headers.assert_called_once()

    # Test for HEAD /health endpoint removed - server now only supports /

    def test_health_check_handler_head_404(self):
        """Test that HEAD invalid paths return 404."""
        handler = mock.MagicMock()
        handler.path = '/invalid'
        handler.send_response = mock.MagicMock()
        handler.send_header = mock.MagicMock()
        handler.end_headers = mock.MagicMock()

        HealthCheckHandler.do_HEAD(handler)

        handler.send_response.assert_called_with(404)
        handler.send_header.assert_called_with('Content-Type', 'text/plain')
        handler.end_headers.assert_called_once()

    def test_health_check_handler_log_message(self):
        """Test custom log message format."""
        handler = mock.MagicMock()
        handler.path = '/'

        # Test that log_message doesn't raise an exception
        HealthCheckHandler.log_message(handler, "test %s", "message")

    def test_timeout_http_server_creation(self):
        """Test that TimeoutHTTPServer can be created."""
        server = TimeoutHTTPServer(('localhost', 0), HealthCheckHandler, timeout=10)
        assert server.timeout == 10
        assert server.start_time > 0
        server.server_close()

    def test_timeout_http_server_verify_request(self):
        """Test that TimeoutHTTPServer verify_request works correctly."""
        server = TimeoutHTTPServer(('localhost', 0), HealthCheckHandler, timeout=10)

        # Test that verify_request returns True when within timeout
        result = server.verify_request(None, None)
        assert result is True

        # Test that verify_request returns False when timeout exceeded
        with mock.patch('time.time', return_value=server.start_time + 11):
            result = server.verify_request(None, None)
            assert result is False

        server.server_close()

    def test_create_health_check_server_oserror(self):
        """Test create_health_check_server with OSError."""
        from neurons.Validator.health_check_server import create_health_check_server

        # Mock OSError when creating server
        with mock.patch('neurons.Validator.health_check_server.TimeoutHTTPServer', side_effect=OSError(98, "Address already in use")):
            with pytest.raises(SystemExit):
                create_health_check_server(8080, 60, 'localhost')

    def test_create_health_check_server_permission_denied(self):
        """Test create_health_check_server with permission denied."""
        from neurons.Validator.health_check_server import create_health_check_server

        # Mock OSError with permission denied
        with mock.patch('neurons.Validator.health_check_server.TimeoutHTTPServer', side_effect=OSError(13, "Permission denied")):
            with pytest.raises(SystemExit):
                create_health_check_server(8080, 60, 'localhost')

    def test_create_health_check_server_keyboard_interrupt(self):
        """Test create_health_check_server with KeyboardInterrupt."""
        from neurons.Validator.health_check_server import create_health_check_server

        # Mock KeyboardInterrupt
        with mock.patch('neurons.Validator.health_check_server.TimeoutHTTPServer') as mock_server_class:
            mock_server = mock.MagicMock()
            mock_server.serve_forever.side_effect = KeyboardInterrupt()
            mock_server_class.return_value = mock_server

            # The function should exit with SystemExit but not raise it in test
            try:
                create_health_check_server(8080, 60, 'localhost')
            except SystemExit:
                pass  # Expected behavior

            mock_server.shutdown.assert_called_once()
            mock_server.server_close.assert_called_once()

    def test_create_health_check_server_unexpected_error(self):
        """Test create_health_check_server with unexpected error."""
        from neurons.Validator.health_check_server import create_health_check_server

        # Mock unexpected exception
        with mock.patch('neurons.Validator.health_check_server.TimeoutHTTPServer', side_effect=Exception("Unexpected error")):
            with pytest.raises(SystemExit):
                create_health_check_server(8080, 60, 'localhost')
