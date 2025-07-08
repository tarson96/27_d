import pytest
import requests
from unittest import mock

from neurons.Validator.health_check_server import (
    HealthCheckHandler,
    TimeoutHTTPServer
)


# --- Fixtures for common objects ---

@pytest.fixture
def mock_ssh_client():
    """Returns a mock SSH client."""
    mock_ssh = mock.MagicMock()
    mock_ssh.connect.return_value = None
    return mock_ssh


@pytest.fixture
def mock_channel():
    """Returns a mock channel."""
    mock_channel = mock.MagicMock()
    mock_channel.closed = False
    mock_channel.recv_ready.return_value = False
    mock_channel.recv_stderr_ready.return_value = False
    return mock_channel


@pytest.fixture
def mock_transport():
    """Returns a mock transport."""
    mock_transport = mock.MagicMock()
    return mock_transport


@pytest.fixture
def mock_axon():
    """Returns a mock axon."""
    axon = mock.MagicMock()
    axon.hotkey = "test_hotkey"
    return axon


@pytest.fixture
def miner_info():
    """Returns test miner info."""
    return {
        'host': 'localhost',
        'port': 22,
        'username': 'test',
        'password': 'test',
        'fixed_external_user_port': 27015
    }


@pytest.fixture
def config_data():
    """Returns empty config data."""
    return {}


@pytest.fixture
def mock_health_check_functions():
    """Mocks all health check functions."""
    mock_upload_script = mock.MagicMock(return_value=True)
    mock_start_server = mock.MagicMock(return_value=(True, mock.MagicMock()))
    mock_wait_ready = mock.MagicMock(return_value=True)
    mock_wait_health = mock.MagicMock(return_value=True)
    mock_kill_server = mock.MagicMock(return_value=True)

    patcher1 = mock.patch('neurons.Validator.health_check.upload_health_check_script', mock_upload_script)
    patcher2 = mock.patch('neurons.Validator.health_check.start_health_check_server_background', mock_start_server)
    patcher3 = mock.patch('neurons.Validator.health_check.wait_for_server_ready_signal', mock_wait_ready)
    patcher4 = mock.patch('neurons.Validator.health_check.wait_for_health_check', mock_wait_health)
    patcher5 = mock.patch('neurons.Validator.health_check.kill_health_check_server', mock_kill_server)
    patcher6 = mock.patch('time.sleep', return_value=None)

    patcher1.start()
    patcher2.start()
    patcher3.start()
    patcher4.start()
    patcher5.start()
    patcher6.start()

    yield {
        'upload_script': mock_upload_script,
        'start_server': mock_start_server,
        'wait_ready': mock_wait_ready,
        'wait_health': mock_wait_health,
        'kill_server': mock_kill_server
    }

    patcher6.stop()
    patcher5.stop()
    patcher4.stop()
    patcher3.stop()
    patcher2.stop()
    patcher1.stop()


@pytest.fixture
def mock_paramiko():
    """Mocks paramiko SSH client."""
    mock_ssh = mock.MagicMock()
    mock_ssh.connect.return_value = None

    patcher = mock.patch('paramiko.SSHClient', return_value=mock_ssh)
    patcher.start()

    yield mock_ssh

    patcher.stop()


@pytest.fixture
def mock_time():
    """Mocks time functions to speed up tests."""
    patcher1 = mock.patch('time.time', side_effect=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11])
    patcher2 = mock.patch('time.sleep', return_value=None)

    patcher1.start()
    patcher2.start()

    yield

    patcher2.stop()
    patcher1.stop()


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

    def test_health_check_handler_get_health(self):
        """Test that GET /health returns 200 OK."""
        handler = mock.MagicMock()
        handler.path = '/health'
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

    def test_health_check_handler_head_health(self):
        """Test that HEAD /health returns 200 OK."""
        handler = mock.MagicMock()
        handler.path = '/health'
        handler.send_response = mock.MagicMock()
        handler.send_header = mock.MagicMock()
        handler.end_headers = mock.MagicMock()

        HealthCheckHandler.do_HEAD(handler)

        handler.send_response.assert_called_with(200)
        handler.send_header.assert_called_with('Content-Type', 'text/plain')
        handler.end_headers.assert_called_once()

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


# ============================================================================
# TESTS FOR VALIDATOR HEALTH CHECK (SSH and HTTP Client Component)
# ============================================================================

class TestValidatorHealthCheck:
    """Tests for the validator health check component (SSH and HTTP client)."""

    def test_upload_health_check_script_success(self, mock_ssh_client):
        """Test successful script upload."""
        from neurons.Validator.health_check import upload_health_check_script

        mock_sftp = mock.MagicMock()
        mock_ssh_client.open_sftp.return_value = mock_sftp

        result = upload_health_check_script(mock_ssh_client, "test_script.py")

        assert result is True
        mock_sftp.put.assert_called_once_with("test_script.py", "/tmp/health_check_server.py")
        mock_sftp.chmod.assert_called_once_with("/tmp/health_check_server.py", 0o755)
        mock_sftp.close.assert_called_once()

    def test_upload_health_check_script_failure(self, mock_ssh_client):
        """Test script upload failure."""
        from neurons.Validator.health_check import upload_health_check_script

        mock_ssh_client.open_sftp.side_effect = Exception("SFTP error")

        result = upload_health_check_script(mock_ssh_client, "test_script.py")

        assert result is False

    def test_start_health_check_server_background_success(self, mock_ssh_client, mock_channel, mock_transport):
        """Test successful background server start."""
        from neurons.Validator.health_check import start_health_check_server_background

        mock_transport.open_session.return_value = mock_channel
        mock_ssh_client.get_transport.return_value = mock_transport

        result, channel = start_health_check_server_background(mock_ssh_client, 8080)

        assert result is True
        assert channel == mock_channel
        mock_channel.exec_command.assert_called_once_with("python3 /tmp/health_check_server.py --port 8080 --timeout 60")

    def test_start_health_check_server_background_channel_closed(self, mock_ssh_client, mock_channel, mock_transport):
        """Test server start with closed channel."""
        from neurons.Validator.health_check import start_health_check_server_background

        mock_channel.closed = True
        mock_channel.recv_ready.return_value = False
        mock_channel.recv_stderr_ready.return_value = False
        mock_transport.open_session.return_value = mock_channel
        mock_ssh_client.get_transport.return_value = mock_transport

        result, channel = start_health_check_server_background(mock_ssh_client, 8080)

        assert result is False
        assert channel is None
        mock_channel.close.assert_called_once()

    def test_start_health_check_server_background_channel_closed_with_output(self, mock_ssh_client, mock_channel, mock_transport):
        """Test server start with closed channel that has output."""
        from neurons.Validator.health_check import start_health_check_server_background

        mock_channel.closed = True
        # Configure mocks to return True only once, then False to avoid infinite loops
        mock_channel.recv_ready.side_effect = [True, False]
        mock_channel.recv_stderr_ready.side_effect = [True, False]
        mock_channel.recv.return_value = b"error output"
        mock_channel.recv_stderr.return_value = b"stderr output"
        mock_transport.open_session.return_value = mock_channel
        mock_ssh_client.get_transport.return_value = mock_transport

        result, channel = start_health_check_server_background(mock_ssh_client, 8080)

        assert result is False
        assert channel is None
        mock_channel.close.assert_called_once()

    def test_start_health_check_server_background_exception(self, mock_ssh_client):
        """Test server start with exception."""
        from neurons.Validator.health_check import start_health_check_server_background

        mock_ssh_client.get_transport.side_effect = Exception("Transport error")

        result, channel = start_health_check_server_background(mock_ssh_client, 8080)

        assert result is False
        assert channel is None

    def test_start_health_check_server_background_exception_in_finally(self, mock_ssh_client):
        """Test start_health_check_server_background with exception in finally block."""
        from neurons.Validator.health_check import start_health_check_server_background

        mock_ssh_client.get_transport.side_effect = Exception("Transport error")

        result, channel = start_health_check_server_background(mock_ssh_client, 8080)

        assert result is False
        assert channel is None

    def test_read_channel_output_success(self, mock_channel):
        """Test successful channel output reading."""
        from neurons.Validator.health_check import read_channel_output

        read_channel_output(mock_channel, "test_hotkey")

        mock_channel.recv_ready.assert_called()
        mock_channel.recv_stderr_ready.assert_called()

    def test_read_channel_output_with_data(self, mock_channel):
        """Test channel output reading with actual data."""
        from neurons.Validator.health_check import read_channel_output

        mock_channel.recv_ready.side_effect = [True, False]
        mock_channel.recv_stderr_ready.side_effect = [True, False]
        mock_channel.recv.return_value = b"test output"
        mock_channel.recv_stderr.return_value = b"error output"

        read_channel_output(mock_channel, "test_hotkey")

        mock_channel.recv.assert_called()
        mock_channel.recv_stderr.assert_called()

    def test_read_channel_output_exception(self, mock_channel):
        """Test channel output reading with exception."""
        from neurons.Validator.health_check import read_channel_output

        mock_channel.recv_ready.side_effect = [True, False]
        mock_channel.recv.side_effect = Exception("Channel error")

        read_channel_output(mock_channel, "test_hotkey")

    def test_kill_health_check_server_success(self, mock_ssh_client):
        """Test successful server kill."""
        from neurons.Validator.health_check import kill_health_check_server

        mock_stdin = mock.MagicMock()
        mock_stdout = mock.MagicMock()
        mock_stderr = mock.MagicMock()
        mock_channel = mock.MagicMock()
        mock_channel.recv_exit_status.return_value = 0
        mock_stdout.channel = mock_channel

        mock_ssh_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

        result = kill_health_check_server(mock_ssh_client, 8080)

        assert result is True
        mock_ssh_client.exec_command.assert_called_once_with("pkill -f 'python3 /tmp/health_check_server.py --port 8080' > /dev/null 2>&1")

    def test_kill_health_check_server_not_running(self, mock_ssh_client):
        """Test server kill when not running."""
        from neurons.Validator.health_check import kill_health_check_server

        mock_stdin = mock.MagicMock()
        mock_stdout = mock.MagicMock()
        mock_stderr = mock.MagicMock()
        mock_channel = mock.MagicMock()
        mock_channel.recv_exit_status.return_value = 1
        mock_stdout.channel = mock_channel

        mock_ssh_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

        result = kill_health_check_server(mock_ssh_client, 8080)

        assert result is True

    def test_kill_health_check_server_exception(self, mock_ssh_client):
        """Test server kill with exception."""
        from neurons.Validator.health_check import kill_health_check_server

        mock_ssh_client.exec_command.side_effect = Exception("SSH error")

        result = kill_health_check_server(mock_ssh_client, 8080)

        assert result is False

    def test_wait_for_server_ready_signal_success(self, mock_time):
        """Test successful server ready signal detection."""
        from neurons.Validator.health_check import wait_for_server_ready_signal

        mock_channel = mock.MagicMock()
        mock_channel.closed = False
        mock_channel.recv_ready.side_effect = [True, False]
        mock_channel.recv_stderr_ready.return_value = False
        mock_channel.recv.return_value = b"Health check server: Ready - endpoints: /health, /"

        result = wait_for_server_ready_signal(mock_channel, "Health check server: Ready - endpoints: /health, /", 10, "test_hotkey")

        assert result is True

    def test_wait_for_server_ready_signal_channel_closed(self, mock_time):
        """Test server ready signal when channel closes unexpectedly."""
        from neurons.Validator.health_check import wait_for_server_ready_signal

        mock_channel = mock.MagicMock()
        mock_channel.closed = True
        mock_channel.recv_ready.return_value = False
        mock_channel.recv_stderr_ready.return_value = False

        result = wait_for_server_ready_signal(mock_channel, "Health check server: Ready - endpoints: /health, /", 10, "test_hotkey")

        assert result is False

    def test_wait_for_server_ready_signal_channel_closed_with_output(self, mock_time):
        """Test server ready signal when channel closes with buffered output."""
        from neurons.Validator.health_check import wait_for_server_ready_signal

        mock_channel = mock.MagicMock()
        mock_channel.closed = True
        mock_channel.recv_ready.side_effect = [True, False]
        mock_channel.recv_stderr_ready.return_value = False
        mock_channel.recv.return_value = b"Some output but not the expected signal"

        result = wait_for_server_ready_signal(mock_channel, "Health check server: Ready - endpoints: /health, /", 10, "test_hotkey")

        assert result is False

    def test_wait_for_server_ready_signal_exception(self, mock_time):
        """Test server ready signal with exception during reading."""
        from neurons.Validator.health_check import wait_for_server_ready_signal

        mock_channel = mock.MagicMock()
        mock_channel.closed = False
        mock_channel.recv_ready.side_effect = Exception("Channel error")

        result = wait_for_server_ready_signal(mock_channel, "Health check server: Ready - endpoints: /health, /", 10, "test_hotkey")

        assert result is False

    def test_wait_for_server_ready_signal_timeout(self):
        """Test server ready signal timeout."""
        from neurons.Validator.health_check import wait_for_server_ready_signal

        mock_channel = mock.MagicMock()
        mock_channel.closed = False
        mock_channel.recv_ready.return_value = False
        mock_channel.recv_stderr_ready.return_value = False

        # Mock time to simulate timeout - provide more values for logging calls
        with mock.patch('time.time', side_effect=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]), \
             mock.patch('time.sleep', return_value=None):
            result = wait_for_server_ready_signal(mock_channel, "Health check server: Ready - endpoints: /health, /", 10, "test_hotkey")

        assert result is False

    def test_wait_for_server_ready_signal_with_stderr_output(self, mock_time):
        """Test server ready signal with stderr output."""
        from neurons.Validator.health_check import wait_for_server_ready_signal

        mock_channel = mock.MagicMock()
        mock_channel.closed = False
        mock_channel.recv_ready.return_value = False
        mock_channel.recv_stderr_ready.side_effect = [True, False]
        mock_channel.recv_stderr.return_value = b"Health check server: Ready - endpoints: /health, /"

        result = wait_for_server_ready_signal(mock_channel, "Health check server: Ready - endpoints: /health, /", 10, "test_hotkey")

        assert result is True

    def test_wait_for_health_check_success(self, mock_time):
        """Test successful HTTP health check."""
        from neurons.Validator.health_check import wait_for_health_check

        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Health OK"

        with mock.patch('requests.get', return_value=mock_response):
            result = wait_for_health_check("localhost", 8080, 10)

        assert result is True

    def test_wait_for_health_check_connection_error(self, mock_time):
        """Test HTTP health check with connection error."""
        from neurons.Validator.health_check import wait_for_health_check

        with mock.patch('requests.get', side_effect=requests.exceptions.ConnectionError()):
            result = wait_for_health_check("localhost", 8080, 10)

        assert result is False

    def test_wait_for_health_check_timeout_error(self, mock_time):
        """Test HTTP health check with timeout error."""
        from neurons.Validator.health_check import wait_for_health_check

        with mock.patch('requests.get', side_effect=requests.exceptions.Timeout()):
            result = wait_for_health_check("localhost", 8080, 10)

        assert result is False

    def test_wait_for_health_check_request_exception(self, mock_time):
        """Test HTTP health check with request exception."""
        from neurons.Validator.health_check import wait_for_health_check

        with mock.patch('requests.get', side_effect=requests.exceptions.RequestException()):
            result = wait_for_health_check("localhost", 8080, 10)

        assert result is False

    def test_wait_for_health_check_non_200_status(self, mock_time):
        """Test HTTP health check with non-200 status."""
        from neurons.Validator.health_check import wait_for_health_check

        mock_response = mock.MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Server Error"

        with mock.patch('requests.get', return_value=mock_response):
            result = wait_for_health_check("localhost", 8080, 10)

        assert result is False

    def test_wait_for_health_check_timeout_reached(self):
        """Test wait_for_health_check when timeout is reached."""
        from neurons.Validator.health_check import wait_for_health_check

        # Mock time to simulate timeout - provide more values for logging calls
        with mock.patch('time.time', side_effect=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31]), \
             mock.patch('requests.get', side_effect=requests.exceptions.ConnectionError()), \
             mock.patch('time.sleep', return_value=None):
            result = wait_for_health_check("localhost", 8080, 30)

        assert result is False


# ============================================================================
# TESTS FOR HEALTH CHECK INTEGRATION (Complete Flow)
# ============================================================================

class TestHealthCheckIntegration:
    """Integration tests for complete health check flow."""

    def test_perform_health_check_success(self, mock_health_check_functions, mock_paramiko, mock_axon, miner_info, config_data):
        """Test successful health check execution."""
        from neurons.Validator.health_check import perform_health_check

        result = perform_health_check(mock_axon, miner_info, config_data)

        assert result is True
        mock_health_check_functions['upload_script'].assert_called_once()
        mock_health_check_functions['start_server'].assert_called_once()
        mock_health_check_functions['wait_ready'].assert_called_once()
        mock_health_check_functions['wait_health'].assert_called_once()
        mock_health_check_functions['kill_server'].assert_called_once()

    def test_perform_health_check_ssh_failure(self, mock_paramiko, mock_axon, miner_info, config_data):
        """Test health check failure when SSH connection fails."""
        from neurons.Validator.health_check import perform_health_check

        mock_paramiko.connect.side_effect = Exception("SSH connection failed")

        result = perform_health_check(mock_axon, miner_info, config_data)

        assert result is False

    def test_perform_health_check_server_start_failure(self, mock_paramiko, mock_axon, miner_info, config_data):
        """Test health check failure when server fails to start."""
        from neurons.Validator.health_check import perform_health_check

        mock_start_server = mock.MagicMock(return_value=(False, None))
        mock_upload_script = mock.MagicMock(return_value=True)

        with mock.patch('neurons.Validator.health_check.upload_health_check_script', mock_upload_script), \
             mock.patch('neurons.Validator.health_check.start_health_check_server_background', mock_start_server), \
             mock.patch('time.sleep', return_value=None):

            result = perform_health_check(mock_axon, miner_info, config_data)

            assert result is False

    def test_perform_health_check_upload_failure(self, mock_paramiko, mock_axon, miner_info, config_data):
        """Test health check failure when script upload fails."""
        from neurons.Validator.health_check import perform_health_check

        mock_upload_script = mock.MagicMock(return_value=False)

        with mock.patch('neurons.Validator.health_check.upload_health_check_script', mock_upload_script), \
             mock.patch('time.sleep', return_value=None):

            result = perform_health_check(mock_axon, miner_info, config_data)

            assert result is False

    def test_perform_health_check_exception(self, mock_paramiko, mock_axon, miner_info, config_data):
        """Test health check with unexpected exception."""
        from neurons.Validator.health_check import perform_health_check

        mock_upload_script = mock.MagicMock(side_effect=Exception("Unexpected error"))

        with mock.patch('neurons.Validator.health_check.upload_health_check_script', mock_upload_script), \
             mock.patch('time.sleep', return_value=None):

            result = perform_health_check(mock_axon, miner_info, config_data)

            assert result is False

    def test_perform_health_check_server_not_ready(self, mock_paramiko, mock_axon, miner_info, config_data):
        """Test health check when server doesn't signal readiness."""
        from neurons.Validator.health_check import perform_health_check

        mock_upload_script = mock.MagicMock(return_value=True)
        mock_start_server = mock.MagicMock(return_value=(True, mock.MagicMock()))
        mock_wait_ready = mock.MagicMock(return_value=False)  # Server not ready

        with mock.patch('neurons.Validator.health_check.upload_health_check_script', mock_upload_script), \
             mock.patch('neurons.Validator.health_check.start_health_check_server_background', mock_start_server), \
             mock.patch('neurons.Validator.health_check.wait_for_server_ready_signal', mock_wait_ready), \
             mock.patch('time.sleep', return_value=None):

            result = perform_health_check(mock_axon, miner_info, config_data)

            assert result is False

    def test_perform_health_check_http_check_failure(self, mock_paramiko, mock_axon, miner_info, config_data):
        """Test health check when HTTP health check fails."""
        from neurons.Validator.health_check import perform_health_check

        mock_upload_script = mock.MagicMock(return_value=True)
        mock_start_server = mock.MagicMock(return_value=(True, mock.MagicMock()))
        mock_wait_ready = mock.MagicMock(return_value=True)
        mock_wait_health = mock.MagicMock(return_value=False)  # HTTP check fails
        mock_kill_server = mock.MagicMock(return_value=True)

        with mock.patch('neurons.Validator.health_check.upload_health_check_script', mock_upload_script), \
             mock.patch('neurons.Validator.health_check.start_health_check_server_background', mock_start_server), \
             mock.patch('neurons.Validator.health_check.wait_for_server_ready_signal', mock_wait_ready), \
             mock.patch('neurons.Validator.health_check.wait_for_health_check', mock_wait_health), \
             mock.patch('neurons.Validator.health_check.kill_health_check_server', mock_kill_server), \
             mock.patch('time.sleep', return_value=None):

            result = perform_health_check(mock_axon, miner_info, config_data)

            assert result is False

    def test_perform_health_check_kill_server_failure(self, mock_paramiko, mock_axon, miner_info, config_data):
        """Test health check when killing server fails but health check succeeds."""
        from neurons.Validator.health_check import perform_health_check

        mock_upload_script = mock.MagicMock(return_value=True)
        mock_start_server = mock.MagicMock(return_value=(True, mock.MagicMock()))
        mock_wait_ready = mock.MagicMock(return_value=True)
        mock_wait_health = mock.MagicMock(return_value=True)
        mock_kill_server = mock.MagicMock(return_value=False)  # Kill server fails

        with mock.patch('neurons.Validator.health_check.upload_health_check_script', mock_upload_script), \
             mock.patch('neurons.Validator.health_check.start_health_check_server_background', mock_start_server), \
             mock.patch('neurons.Validator.health_check.wait_for_server_ready_signal', mock_wait_ready), \
             mock.patch('neurons.Validator.health_check.wait_for_health_check', mock_wait_health), \
             mock.patch('neurons.Validator.health_check.kill_health_check_server', mock_kill_server), \
             mock.patch('time.sleep', return_value=None):

            result = perform_health_check(mock_axon, miner_info, config_data)

            assert result is True  # Should still succeed even if kill fails

    def test_perform_health_check_unexpected_exception(self, mock_paramiko, mock_axon, miner_info, config_data):
        """Test health check with unexpected exception in main flow."""
        from neurons.Validator.health_check import perform_health_check

        # Mock successful SSH connection but exception in main flow
        mock_upload_script = mock.MagicMock(side_effect=Exception("Unexpected error in upload"))

        with mock.patch('neurons.Validator.health_check.upload_health_check_script', mock_upload_script), \
             mock.patch('time.sleep', return_value=None):

            result = perform_health_check(mock_axon, miner_info, config_data)

            assert result is False

    def test_perform_health_check_channel_output_reading(self, mock_paramiko, mock_axon, miner_info, config_data):
        """Test health check with channel output reading after HTTP check."""
        from neurons.Validator.health_check import perform_health_check

        mock_channel = mock.MagicMock()
        mock_channel.closed = False

        mock_upload_script = mock.MagicMock(return_value=True)
        mock_start_server = mock.MagicMock(return_value=(True, mock_channel))
        mock_wait_ready = mock.MagicMock(return_value=True)
        mock_wait_health = mock.MagicMock(return_value=True)
        mock_kill_server = mock.MagicMock(return_value=True)
        mock_read_output = mock.MagicMock()

        with mock.patch('neurons.Validator.health_check.upload_health_check_script', mock_upload_script), \
             mock.patch('neurons.Validator.health_check.start_health_check_server_background', mock_start_server), \
             mock.patch('neurons.Validator.health_check.wait_for_server_ready_signal', mock_wait_ready), \
             mock.patch('neurons.Validator.health_check.wait_for_health_check', mock_wait_health), \
             mock.patch('neurons.Validator.health_check.kill_health_check_server', mock_kill_server), \
             mock.patch('neurons.Validator.health_check.read_channel_output', mock_read_output), \
             mock.patch('time.sleep', return_value=None):

            result = perform_health_check(mock_axon, miner_info, config_data)

            assert result is True
            mock_read_output.assert_called()

    def test_perform_health_check_channel_closed_after_http_check(self, mock_paramiko, mock_axon, miner_info, config_data):
        """Test health check when channel is closed after HTTP check."""
        from neurons.Validator.health_check import perform_health_check

        mock_channel = mock.MagicMock()
        mock_channel.closed = True  # Channel closed after HTTP check

        mock_upload_script = mock.MagicMock(return_value=True)
        mock_start_server = mock.MagicMock(return_value=(True, mock_channel))
        mock_wait_ready = mock.MagicMock(return_value=True)
        mock_wait_health = mock.MagicMock(return_value=True)
        mock_kill_server = mock.MagicMock(return_value=True)

        with mock.patch('neurons.Validator.health_check.upload_health_check_script', mock_upload_script), \
             mock.patch('neurons.Validator.health_check.start_health_check_server_background', mock_start_server), \
             mock.patch('neurons.Validator.health_check.wait_for_server_ready_signal', mock_wait_ready), \
             mock.patch('neurons.Validator.health_check.wait_for_health_check', mock_wait_health), \
             mock.patch('neurons.Validator.health_check.kill_health_check_server', mock_kill_server), \
             mock.patch('time.sleep', return_value=None):

            result = perform_health_check(mock_axon, miner_info, config_data)

            assert result is True

    def test_perform_health_check_channel_output_after_kill(self, mock_paramiko, mock_axon, miner_info, config_data):
        """Test health check with channel output reading after server kill."""
        from neurons.Validator.health_check import perform_health_check

        mock_channel = mock.MagicMock()
        mock_channel.closed = False

        mock_upload_script = mock.MagicMock(return_value=True)
        mock_start_server = mock.MagicMock(return_value=(True, mock_channel))
        mock_wait_ready = mock.MagicMock(return_value=True)
        mock_wait_health = mock.MagicMock(return_value=True)
        mock_kill_server = mock.MagicMock(return_value=True)
        mock_read_output = mock.MagicMock()

        with mock.patch('neurons.Validator.health_check.upload_health_check_script', mock_upload_script), \
             mock.patch('neurons.Validator.health_check.start_health_check_server_background', mock_start_server), \
             mock.patch('neurons.Validator.health_check.wait_for_server_ready_signal', mock_wait_ready), \
             mock.patch('neurons.Validator.health_check.wait_for_health_check', mock_wait_health), \
             mock.patch('neurons.Validator.health_check.kill_health_check_server', mock_kill_server), \
             mock.patch('neurons.Validator.health_check.read_channel_output', mock_read_output), \
             mock.patch('time.sleep', return_value=None):

            result = perform_health_check(mock_axon, miner_info, config_data)

            assert result is True
            # Should be called twice: after HTTP check and after kill
            assert mock_read_output.call_count == 2
