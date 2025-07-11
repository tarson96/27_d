#!/usr/bin/env python3
"""
Health Check Module

This module handles healthcheck independently from POG (Proof of Generation).
It runs after POG has finished to verify miner connectivity.
"""

import paramiko
import time
import bittensor as bt
import requests

def upload_health_check_script(ssh_client, health_check_script_path):
    """
    Uploads the health check script to the miner using SFTP.

    Args:
        ssh_client (paramiko.SSHClient): SSH client connected to the miner
        health_check_script_path (str): Local path of the health check script

    Returns:
        bool: True if uploaded successfully, False otherwise
    """
    try:
        sftp = ssh_client.open_sftp()
        sftp.put(health_check_script_path, "/tmp/health_check_server.py")
        sftp.chmod("/tmp/health_check_server.py", 0o755)
        sftp.close()
        return True
    except Exception as e:
        bt.logging.error(f"Error uploading health check script: {e}")
        return False

def start_health_check_server_background(ssh_client, port=27015, timeout=60):
    """
    Starts the health check server using Paramiko channels.

    Args:
        ssh_client (paramiko.SSHClient): SSH client connected to the miner
        port (int): Port for the health check server
        timeout (int): Wait time in seconds (default 60 seconds)

    Returns:
        tuple: (bool, channel) - (True if started successfully, channel object)
    """
    channel = None
    try:
        # Use paramiko transport and channel
        transport = ssh_client.get_transport()
        channel = transport.open_session()

        # Execute the health check server command using channel
        command = f"python3 /tmp/health_check_server.py --port {port} --timeout {timeout}"
        bt.logging.trace(f"Executing remote command: {command}")
        channel.exec_command(command)

        # Check if the channel is still active (server is running)
        if not channel.closed:
            bt.logging.trace("Remote server channel is open.")
            return True, channel
        else:
            # If the channel closed immediately, it means the command failed to start the server.
            # Collect *all* output for debugging this immediate failure.
            stdout_output = ""
            stderr_output = ""
            while channel.recv_ready():
                stdout_output += channel.recv(4096).decode('utf-8', errors='ignore')
            while channel.recv_stderr_ready():
                stderr_output += channel.recv_stderr(4096).decode('utf-8', errors='ignore')

            bt.logging.error(f"Health check server channel is closed immediately after exec_command (server likely crashed on startup).")
            if stdout_output:
                bt.logging.error(f"Server stdout on immediate close: {stdout_output.strip()}")
            if stderr_output:
                bt.logging.error(f"Server stderr on immediate close: {stderr_output.strip()}")

            if channel:
                channel.close()
            return False, None

    except Exception as e:
        bt.logging.error(f"Error starting health check server: {e}")
        if channel:
            channel.close()
        return False, None

def read_channel_output(channel, hotkey=""):
    """
    Reads and logs *all available* output from the channel's stdout and stderr streams
    without blocking indefinitely. This function is designed to drain the buffers.

    Args:
        channel: Paramiko channel object
        hotkey (str): Hotkey for logging context
    """
    current_stdout = ""
    current_stderr = ""

    try:
        # Read all available stdout
        while channel.recv_ready():
            current_stdout += channel.recv(4096).decode('utf-8', errors='ignore')

        # Read all available stderr
        while channel.recv_stderr_ready():
            current_stderr += channel.recv_stderr(4096).decode('utf-8', errors='ignore')

        # Log any output found in this cycle
        if current_stdout:
            bt.logging.trace(f"{hotkey}: Health check server stdout: {current_stdout.strip()}")
        if current_stderr:
            bt.logging.trace(f"{hotkey}: Health check server stderr: {current_stderr.strip()}")

    except Exception as e:
        bt.logging.trace(f"{hotkey}: Error reading channel output: {e}")


def wait_for_port_ready(ssh_client, port=27015, timeout=30, hotkey=""):
    """
    Waits for a health endpoint to become available using urllib.request.

    This function checks if the health check server is responding by making
    HTTP requests to the root endpoint (/) on the specified port.

    Args:
        ssh_client (paramiko.SSHClient): SSH client connected to the miner
        port (int): Port to check
        timeout (int): Maximum time to wait in seconds
        hotkey (str): Hotkey for logging context

    Returns:
        bool: True if health endpoint becomes available within timeout, False otherwise
    """
    start_time = time.time()
    check_interval = 1

    while time.time() - start_time < timeout:
        try:
            command = f'python3 -c \'import urllib.request; urllib.request.urlopen("http://127.0.0.1:{port}/", timeout=2)\''
            bt.logging.trace(f"{hotkey}: Checking health endpoint on port {port} (path /)")

            stdin, stdout, stderr = ssh_client.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()

            if exit_status == 0:
                bt.logging.info(f"{hotkey}: Health endpoint on port {port} (path /) is now responding")
                return True

        except Exception as e:
            bt.logging.trace(f"{hotkey}: Error checking health endpoint: {e}")

        time.sleep(check_interval)

    bt.logging.error(f"{hotkey}: Health endpoint on port {port} (path /) did not become available within {timeout} seconds")
    return False

def kill_health_check_server(ssh_client, port=27015):
    """
    Kills the health check server process using PID file.

    Args:
        ssh_client (paramiko.SSHClient): SSH client connected to the miner
        port (int): Port of the health check server

    Returns:
        bool: True if killed successfully, False otherwise
    """
    try:
        pid_file_path = f"/tmp/health_check_server_{port}.pid"

        # Read PID from file
        stdin, stdout, stderr = ssh_client.exec_command(f"cat {pid_file_path} 2>/dev/null || echo ''")
        pid_output = stdout.read().decode('utf-8').strip()

        if not pid_output:
            bt.logging.trace(f"Health check server PID file not found, server may not be running")
            return True

        try:
            pid = int(pid_output)
        except ValueError:
            bt.logging.trace(f"Invalid PID in file: {pid_output}")
            return True

        # Kill process using PID
        stdin, stdout, stderr = ssh_client.exec_command(f"kill {pid} 2>/dev/null || echo 'Process not found'")
        exit_status = stdout.channel.recv_exit_status()

        if exit_status == 0:
            bt.logging.trace(f"Health check server (PID: {pid}) killed successfully")
            return True
        else:
            bt.logging.trace(f"Health check server (PID: {pid}) was not running or already killed")
            return True

    except Exception as e:
        bt.logging.trace(f"Error killing health check server: {e}")
        return False

def wait_for_health_check(host, port, timeout=30, retry_interval=1):
    """
    Waits for the health check server to be available via HTTP.

    Args:
        host (str): Miner host
        port (int): Health check server port
        timeout (int): Maximum wait time in seconds
        retry_interval (int): Interval between retries in seconds

    Returns:
        bool: True if health check is successful, False otherwise
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"http://{host}:{port}", timeout=2)

            if response.status_code == 200:
                bt.logging.trace(f"HTTP Health check successful on {host}:{port}!")
                return True
            else:
                bt.logging.error(f"HTTP Health check server returned status code {response.status_code} instead of 200 on {host}:{port}")

        except requests.exceptions.ConnectionError as e:
            bt.logging.trace(f"HTTP Connection error to {host}:{port}: {e}")
        except requests.exceptions.Timeout as e:
            bt.logging.trace(f"HTTP Timeout error to {host}:{port}: {e}")
        except requests.exceptions.RequestException as e:
            bt.logging.trace(f"HTTP Request error to {host}:{port}: {e}")

        time.sleep(retry_interval)

    return False

def perform_health_check(axon, miner_info, config_data):
    """
    Performs health check on a miner after POG has finished.

    Args:
        axon: Axon information of the miner
        miner_info: Miner information (host, port, etc.) - always provided by POG
        config_data: Validator configuration

    Returns:
        bool: True if health check is successful, False otherwise
    """
    hotkey = axon.hotkey
    host = None
    ssh_client = None
    channel = None

    try:
        host = miner_info['host']

        # Connect via SSH
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            bt.logging.trace(f"{hotkey}: Attempting SSH connection to {host}")
            ssh_client.connect(host, port=miner_info.get('port', 22), username=miner_info['username'], password=miner_info['password'], timeout=10)
            bt.logging.trace(f"{hotkey}: SSH connection successful.")
        except Exception as ssh_error:
            bt.logging.info(f"{hotkey}: SSH connection failed during health check: {ssh_error}")
            return False

        health_check_script_path = "neurons/Validator/health_check_server.py"

        if not upload_health_check_script(ssh_client, health_check_script_path):
            bt.logging.error(f"{hotkey}: Failed to upload health check script.")
            return False

        internal_health_check_port = 27015
        bt.logging.trace(f"{hotkey}: Starting health check server in background on port {internal_health_check_port}.")
        server_started, channel = start_health_check_server_background(ssh_client, internal_health_check_port, timeout=60)

        if not server_started or channel is None:
            bt.logging.error(f"{hotkey}: Failed to initiate health check server command or channel is invalid. See errors above.")
            return False

        server_ready_timeout = 15

        bt.logging.info(f"{hotkey}: Attempting to confirm health check server's internal readiness via port check.")
        if not wait_for_port_ready(ssh_client, internal_health_check_port, server_ready_timeout, hotkey):
            bt.logging.error(f"{hotkey}: Health check server did not become ready within {server_ready_timeout} seconds. Aborting health check.")
            return False

        bt.logging.info(f"{hotkey}: Health check server confirmed internally ready via port check.")

        external_health_check_port = miner_info.get('fixed_external_user_port', 27015)
        health_check_timeout = 15
        health_check_retry_interval = 1

        bt.logging.trace(f"{hotkey}: Performing external HTTP health check on {host}:{external_health_check_port}.")

        health_check_success = wait_for_health_check(
            host,
            external_health_check_port,
            timeout=health_check_timeout,
            retry_interval=health_check_retry_interval
        )

        if channel and not channel.closed:
            bt.logging.trace(f"{hotkey}: Reading any further server output after HTTP check completion.")
            read_channel_output(channel, hotkey)

        if not health_check_success:
            bt.logging.error(f"{hotkey}: External HTTP health check server not responding.")
            return False

        bt.logging.trace(f"{hotkey}: Health check successful. Attempting to kill health check server.")
        if kill_health_check_server(ssh_client, internal_health_check_port):
            bt.logging.trace(f"{hotkey}: Health check server successfully terminated.")
            if channel and not channel.closed:
                bt.logging.trace(f"{hotkey}: Reading final server output after termination.")
                read_channel_output(channel, hotkey)
        else:
            bt.logging.warning(f"{hotkey}: Failed to explicitly kill health check server, but check was successful. It might be self-terminating.")

        return True

    except Exception as e:
        bt.logging.info(f"❌ {hotkey}: An unexpected error occurred during health check: {e}")
        return False

    finally:
        if ssh_client is not None:
            try:
                if channel and not channel.closed:
                    bt.logging.trace(f"{hotkey}: Closing Paramiko channel.")
                    channel.close()
                ssh_client.close()
                bt.logging.trace(f"{hotkey}: SSH connection closed.")
            except Exception as e:
                bt.logging.trace(f"{hotkey}: Error closing SSH connection or channel: {e}")
