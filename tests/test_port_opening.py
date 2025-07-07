import pytest
import base64
from unittest import mock

from compute.utils.parser import ComputeArgPaser
from neurons.Miner.container import run_container, INTERNAL_USER_PORT


# --- Dummy Virtual Memory for psutil ---
class DummyVirtualMemory:
    available = 8 * 1024**3  # 8 GB


# --- Fixtures for common objects ---

@pytest.fixture
def mock_containers():
    return []


@pytest.fixture
def docker_client():
    return mock.MagicMock()


@pytest.fixture
def mock_get_docker(mock_containers, docker_client):
    client = docker_client
    client.containers.list = mock.MagicMock(return_value=mock_containers)
    client.images.build = mock.MagicMock(return_value=(None, None))
    client.images.prune = mock.MagicMock()

    patcher_get = mock.patch('neurons.Miner.container.get_docker', return_value=(client, mock_containers))
    patcher_from_env = mock.patch('docker.from_env', return_value=client)

    patcher_get.start()
    patcher_from_env.start()

    yield mock_get_docker

    patcher_from_env.stop()
    patcher_get.stop()


@pytest.fixture
def new_container(mock_containers):
    """A test container in 'created' state with expected name."""
    container = mock.MagicMock()
    container.name = "ssh-test-container"
    container.status = "created"
    mock_containers.append(container)
    return container


@pytest.fixture
def mock_run_container(docker_client, new_container):
    docker_client.containers.run = mock.MagicMock(return_value=new_container)
    return new_container


@pytest.fixture
def mock_open_fn():
    patcher = mock.patch('builtins.open', new_callable=mock.mock_open())
    yield patcher.start()
    patcher.stop()


@pytest.fixture
def mock_container_build(monkeypatch):
    patcher1 = mock.patch('os.makedirs')
    patcher3 = mock.patch('neurons.Miner.container.rsa.encrypt_data', return_value=b"encrypted_data")
    patcher4 = mock.patch('neurons.Miner.container.psutil.virtual_memory', return_value=DummyVirtualMemory())
    patcher5 = mock.patch('neurons.Miner.container.build_sample_container')
    patcher6 = mock.patch('neurons.Miner.container.password_generator', return_value="testpwd")

    # Set module-level globals required by run_container.
    from neurons.Miner import container as cnt
    monkeypatch.setattr(cnt, "image_name_base", "dummy_base")
    monkeypatch.setattr(cnt, "image_name", "dummy_image")
    monkeypatch.setattr(cnt, "__version_as_int__", 1)

    patcher1.start()
    patcher3.start()
    patcher4.start()
    patcher5.start()
    patcher6.start()

    yield

    patcher6.stop()
    patcher5.stop()
    patcher4.stop()
    patcher3.stop()
    patcher1.stop()


# --- Grouped Tests ---

class TestPortOpeningValidation:
    """Tests to validate port opening functionality in the miner."""

    def test_external_fixed_port_default_value(self):
        """Test that verifies the default value of the external port is correct."""
        parser = ComputeArgPaser()
        args = parser.parse_args([])

        assert getattr(args, 'external.fixed_port') == 27015
        assert hasattr(args, 'external.fixed_port')

    def test_external_fixed_port_valid_values(self):
        """Test that verifies that valid port values are accepted."""
        valid_ports = [1, 1024, 8000, 27015, 65535]

        for port in valid_ports:
            parser = ComputeArgPaser()
            args = parser.parse_args([f"--external.fixed-port={port}"])
            assert getattr(args, 'external.fixed_port') == port

    def test_external_fixed_port_non_integer(self):
        """Test that verifies that non-integer values are rejected."""
        invalid_values = ["abc", "12.5", "port", ""]

        for value in invalid_values:
            parser = ComputeArgPaser()
            with pytest.raises(SystemExit):
                parser.parse_args([f"--external.fixed-port={value}"])

    def test_external_fixed_port_success_case(self):
        """Test that verifies the success case with port 8000."""
        parser = ComputeArgPaser()
        args = parser.parse_args(["--external.fixed-port=8000"])

        assert getattr(args, 'external.fixed_port') == 8000

    def test_external_fixed_port_default_value_explicit(self):
        """Test that verifies the default port 27015 works when explicitly specified."""
        parser = ComputeArgPaser()
        args = parser.parse_args(["--external.fixed-port=27015"])

        assert getattr(args, 'external.fixed_port') == 27015


class TestPortOpeningInContainer:
    """Tests to verify that port opening works correctly in the container."""

    def test_container_port_mapping_with_valid_port(
        self,
        mock_container_build,
        mock_get_docker,
        docker_client,
        new_container,
        mock_run_container,
        mock_open_fn,
    ):
        """
        Test that verifies that the external port is correctly mapped to the container.
        """
        # Prepare input parameters
        cpu_usage = {"assignment": "0-1"}
        ram_usage = {"capacity": "5g"}
        hard_disk_usage = {"capacity": "100g"}
        gpu_usage = {"capacity": "all"}
        public_key = "dummy_public_key"
        docker_requirement = {
            "base_image": "dummy_base",
            "volume_path": "/dummy/volume",
            "fixed_external_user_port": 8000,  # Success port - external port 8000
            "dockerfile": ""
        }
        testing = True

        # Call run_container
        result = run_container(cpu_usage, ram_usage, hard_disk_usage, gpu_usage,
                             public_key, docker_requirement, testing)

        # Verify that the image was built and container was run
        docker_client.images.build.assert_called_once()
        docker_client.containers.run.assert_called_once()

        # Verify container configuration
        _, kwargs = docker_client.containers.run.call_args
        assert kwargs.get("name") == "ssh-test-container"  # testing=True
        assert kwargs.get("detach") is True
        assert kwargs.get("init") is True

        # Verify port mapping
        actual_ports = kwargs.get("ports", {})
        assert INTERNAL_USER_PORT in actual_ports
        assert actual_ports[INTERNAL_USER_PORT] == 8000

        # Verify file operations
        mock_open_fn.assert_called_with('allocation_key', 'w')

        # Verify result structure
        expected_info = base64.b64encode(b"encrypted_data").decode("utf-8")
        assert result
        assert result["status"] is True
        assert result["message"] == "Container started successfully."
        assert result["info"] == expected_info

    def test_container_port_mapping_with_default_port(
        self,
        mock_container_build,
        mock_get_docker,
        docker_client,
        new_container,
        mock_run_container,
        mock_open_fn,
    ):
        """
        Test that verifies that when no external port is specified, the default port 27015 is used.
        """
        # Prepare input parameters
        cpu_usage = {"assignment": "0-1"}
        ram_usage = {"capacity": "5g"}
        hard_disk_usage = {"capacity": "100g"}
        gpu_usage = {"capacity": "all"}
        public_key = "dummy_public_key"
        docker_requirement = {
            "base_image": "dummy_base",
            "volume_path": "/dummy/volume",
            "fixed_external_user_port": 27015,  # Default port from parser
            "dockerfile": ""
        }
        testing = True

        # Call run_container
        result = run_container(cpu_usage, ram_usage, hard_disk_usage, gpu_usage,
                             public_key, docker_requirement, testing)

        # Verify that the image was built and container was run
        docker_client.images.build.assert_called_once()
        docker_client.containers.run.assert_called_once()

        # Verify container configuration
        _, kwargs = docker_client.containers.run.call_args
        assert kwargs.get("name") == "ssh-test-container"  # testing=True
        assert kwargs.get("detach") is True
        assert kwargs.get("init") is True

        # Verify port mapping
        actual_ports = kwargs.get("ports", {})
        assert INTERNAL_USER_PORT in actual_ports
        assert actual_ports[INTERNAL_USER_PORT] == 27015

        # Verify file operations
        mock_open_fn.assert_called_with('allocation_key', 'w')

        # Verify result structure
        expected_info = base64.b64encode(b"encrypted_data").decode("utf-8")
        assert result
        assert result["status"] is True
        assert result["message"] == "Container started successfully."
        assert result["info"] == expected_info

    def test_container_run_failure(self, mock_container_build, mock_get_docker, docker_client):
        """Test that container run failure is handled properly."""
        # Mock container run to fail
        docker_client.containers.run.side_effect = Exception("Docker run failed")
        
        # Prepare input parameters
        cpu_usage = {"assignment": "0-1"}
        ram_usage = {"capacity": "5g"}
        hard_disk_usage = {"capacity": "100g"}
        gpu_usage = {"capacity": "all"}
        public_key = "dummy_public_key"
        docker_requirement = {
            "base_image": "dummy_base",
            "volume_path": "/dummy/volume",
            "fixed_external_user_port": 27015,
            "dockerfile": ""
        }
        testing = True

        # Call run_container and expect it to handle the exception
        result = run_container(cpu_usage, ram_usage, hard_disk_usage, gpu_usage,
                             public_key, docker_requirement, testing)

        # Verify result indicates failure
        assert result["status"] is False
        assert "error" in result["message"].lower() or "failed" in result["message"].lower()


if __name__ == "__main__":
    pytest.main([__file__])
