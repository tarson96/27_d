import pytest
from unittest import mock

from neurons.Validator.health_check_server import (
    HealthCheckHandler,
    TimeoutHTTPServer
)


class TestHealthCheckServer:
    """Tests for the health check HTTP server."""

    def test_health_check_handler_get_root(self):
        """Test that GET / returns 200 OK."""
        # Create a mock handler instance with all required attributes
        handler = mock.MagicMock()
        handler.path = '/'
        handler.send_response = mock.MagicMock()
        handler.send_header = mock.MagicMock()
        handler.end_headers = mock.MagicMock()
        handler.wfile = mock.MagicMock()
        
        # Call the method directly
        HealthCheckHandler.do_GET(handler)
        
        handler.send_response.assert_called_with(200)
        handler.send_header.assert_called_with('Content-Type', 'text/plain')
        handler.end_headers.assert_called_once()
        handler.wfile.write.assert_called_with(b"Health OK")

    def test_health_check_handler_get_health(self):
        """Test that GET /health returns 200 OK."""
        # Create a mock handler instance with all required attributes
        handler = mock.MagicMock()
        handler.path = '/health'
        handler.send_response = mock.MagicMock()
        handler.send_header = mock.MagicMock()
        handler.end_headers = mock.MagicMock()
        handler.wfile = mock.MagicMock()
        
        # Call the method directly
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

    def test_timeout_http_server_creation(self):
        """Test that TimeoutHTTPServer can be created."""
        server = TimeoutHTTPServer(('localhost', 0), HealthCheckHandler, timeout=10)
        assert server.timeout == 10
        assert server.start_time > 0
        server.server_close()


class TestHealthCheckValidatorIntegration:
    """Tests for validator integration with health check."""

    def test_perform_health_check_success(self):
        """Test successful health check execution."""
        from neurons.Validator.health_check import perform_health_check
        
        # Mock successful responses
        mock_upload_script = mock.MagicMock(return_value=True)
        mock_start_server = mock.MagicMock(return_value=(True, mock.MagicMock()))
        mock_wait_ready = mock.MagicMock(return_value=True)
        mock_wait_health = mock.MagicMock(return_value=True)
        mock_kill_server = mock.MagicMock(return_value=True)
        
        # Mock SSH client
        mock_ssh = mock.MagicMock()
        mock_ssh.connect.return_value = None
        
        # Create patchers
        patcher1 = mock.patch('neurons.Validator.health_check.upload_health_check_script', mock_upload_script)
        patcher2 = mock.patch('neurons.Validator.health_check.start_health_check_server_background', mock_start_server)
        patcher3 = mock.patch('neurons.Validator.health_check.wait_for_server_ready_signal', mock_wait_ready)
        patcher4 = mock.patch('neurons.Validator.health_check.wait_for_health_check', mock_wait_health)
        patcher5 = mock.patch('neurons.Validator.health_check.kill_health_check_server', mock_kill_server)
        patcher6 = mock.patch('paramiko.SSHClient', return_value=mock_ssh)
        
        # Start patchers
        patcher1.start()
        patcher2.start()
        patcher3.start()
        patcher4.start()
        patcher5.start()
        patcher6.start()
        
        try:
            # Test data
            axon = mock.MagicMock()
            axon.hotkey = "test_hotkey"
            
            miner_info = {
                'host': 'localhost',
                'port': 22,
                'username': 'test',
                'password': 'test',
                'fixed_external_user_port': 27015
            }
            
            config_data = {}
            
            # Execute health check
            result = perform_health_check(axon, miner_info, config_data)
            
            # Verify result
            assert result is True
            
            # Verify all mocks were called
            mock_upload_script.assert_called_once()
            mock_start_server.assert_called_once()
            mock_wait_ready.assert_called_once()
            mock_wait_health.assert_called_once()
            mock_kill_server.assert_called_once()
            
        finally:
            # Stop patchers
            patcher6.stop()
            patcher5.stop()
            patcher4.stop()
            patcher3.stop()
            patcher2.stop()
            patcher1.stop()

    def test_perform_health_check_ssh_failure(self):
        """Test health check failure when SSH connection fails."""
        from neurons.Validator.health_check import perform_health_check
        
        # Mock SSH client that fails to connect
        mock_ssh = mock.MagicMock()
        mock_ssh.connect.side_effect = Exception("SSH connection failed")
        
        # Create patcher
        patcher = mock.patch('paramiko.SSHClient', return_value=mock_ssh)
        patcher.start()
        
        try:
            # Test data
            axon = mock.MagicMock()
            axon.hotkey = "test_hotkey"
            
            miner_info = {
                'host': 'localhost',
                'port': 22,
                'username': 'test',
                'password': 'test',
                'fixed_external_user_port': 27015
            }
            
            config_data = {}
            
            # Execute health check
            result = perform_health_check(axon, miner_info, config_data)
            
            # Verify result is False due to SSH failure
            assert result is False
            
        finally:
            patcher.stop()

    def test_perform_health_check_server_start_failure(self):
        """Test health check failure when server fails to start."""
        from neurons.Validator.health_check import perform_health_check
        
        # Mock successful SSH but failed server start
        mock_ssh = mock.MagicMock()
        mock_ssh.connect.return_value = None
        
        # Mock failed server start
        mock_start_server = mock.MagicMock(return_value=(False, None))
        mock_upload_script = mock.MagicMock(return_value=True)
        
        # Create patchers
        patcher1 = mock.patch('neurons.Validator.health_check.upload_health_check_script', mock_upload_script)
        patcher2 = mock.patch('neurons.Validator.health_check.start_health_check_server_background', mock_start_server)
        patcher3 = mock.patch('paramiko.SSHClient', return_value=mock_ssh)
        
        patcher1.start()
        patcher2.start()
        patcher3.start()
        
        try:
            # Test data
            axon = mock.MagicMock()
            axon.hotkey = "test_hotkey"
            
            miner_info = {
                'host': 'localhost',
                'port': 22,
                'username': 'test',
                'password': 'test',
                'fixed_external_user_port': 27015
            }
            
            config_data = {}
            
            # Execute health check
            result = perform_health_check(axon, miner_info, config_data)
            
            # Verify result is False due to server start failure
            assert result is False
            
        finally:
            patcher3.stop()
            patcher2.stop()
            patcher1.stop()


if __name__ == "__main__":
    pytest.main([__file__]) 