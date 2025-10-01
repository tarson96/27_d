# The MIT License (MIT)
# Copyright © 2023 GitPhantomman

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import base64
import json
import os
import secrets
import string
import subprocess
import sys
import tempfile
import pwd
import grp
import signal
import time
from pathlib import Path

import bittensor as bt

from compute import __version_as_int__
from compute.utils.exceptions import make_error_response
import neurons.RSAEncryption as rsa

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Configuration for containerless mode
INTERNAL_USER_PORT = 27015  # Port for user applications
WORK_DIR = "/tmp/miner_allocations"
SSH_DAEMON_CONFIG = "/tmp/miner_sshd_config"
SSH_HOST_KEY = "/tmp/miner_ssh_host_key"
ACTIVE_ALLOCATION_FILE = "allocation_active"

class AllocationManager:
    def __init__(self):
        self.ssh_daemon_pid = None
        self.ssh_port = None
        self.allocation_user = None
        self.work_directory = None

    def create_work_environment(self, docker_requirement: dict):
        """Create isolated work environment without Docker"""
        try:
            # Create work directory
            work_dir = os.path.join(WORK_DIR, f"allocation_{int(time.time())}")
            os.makedirs(work_dir, exist_ok=True, mode=0o755)

            # Create basic directory structure
            os.makedirs(os.path.join(work_dir, "workspace"), exist_ok=True, mode=0o755)
            os.makedirs(os.path.join(work_dir, "tmp"), exist_ok=True, mode=0o755)

            return work_dir

        except Exception as e:
            bt.logging.error(f"Failed to create work environment: {e}")
            return None

    def setup_ssh_daemon(self, ssh_key: str, ssh_port: int, work_dir: str, password: str):
        """Setup SSH daemon for validator access without Docker"""
        try:
            # Generate SSH host key if not exists
            if not os.path.exists(SSH_HOST_KEY):
                subprocess.run([
                    "ssh-keygen", "-t", "rsa", "-b", "2048",
                    "-f", SSH_HOST_KEY, "-N", "", "-q"
                ], check=True)

            # Create SSH authorized_keys
            ssh_dir = os.path.join(work_dir, ".ssh")
            os.makedirs(ssh_dir, exist_ok=True, mode=0o700)

            authorized_keys_file = os.path.join(ssh_dir, "authorized_keys")
            with open(authorized_keys_file, "w") as f:
                f.write(ssh_key + "\n")
            os.chmod(authorized_keys_file, 0o600)

            # Create SSH daemon configuration
            sshd_config = f"""
Port {ssh_port}
HostKey {SSH_HOST_KEY}
AuthorizedKeysFile {authorized_keys_file}
PermitRootLogin yes
PasswordAuthentication yes
PubkeyAuthentication yes
ChrootDirectory {work_dir}
Subsystem sftp /usr/lib/openssh/sftp-server
AllowUsers root
"""

            with open(SSH_DAEMON_CONFIG, "w") as f:
                f.write(sshd_config)

            # Start SSH daemon
            cmd = [
                "/usr/sbin/sshd", "-D", "-f", SSH_DAEMON_CONFIG,
                "-o", "PidFile=/dev/null"
            ]

            process = subprocess.Popen(
                cmd,
                cwd=work_dir,
                preexec_fn=os.setsid,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )

            # Give it a moment to start
            time.sleep(2)

            if process.poll() is None:
                self.ssh_daemon_pid = process.pid
                return True
            else:
                bt.logging.error("SSH daemon failed to start")
                return False

        except Exception as e:
            bt.logging.error(f"Failed to setup SSH daemon: {e}")
            return False

    def cleanup_allocation(self):
        """Clean up allocation resources"""
        try:
            # Kill SSH daemon
            if self.ssh_daemon_pid:
                try:
                    os.kill(self.ssh_daemon_pid, signal.SIGTERM)
                    time.sleep(2)
                    try:
                        os.kill(self.ssh_daemon_pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                except ProcessLookupError:
                    pass
                self.ssh_daemon_pid = None

            # Clean up work directory
            if self.work_directory and os.path.exists(self.work_directory):
                subprocess.run(["rm", "-rf", self.work_directory], check=True)

            # Clean up SSH config files
            for config_file in [SSH_DAEMON_CONFIG, SSH_HOST_KEY, f"{SSH_HOST_KEY}.pub"]:
                if os.path.exists(config_file):
                    os.remove(config_file)

            return True

        except Exception as e:
            bt.logging.error(f"Error during cleanup: {e}")
            return False

# Global allocation manager instance
allocation_manager = AllocationManager()

def password_generator(length):
    alphabet = string.ascii_letters + string.digits
    random_str = "".join(secrets.choice(alphabet) for _ in range(length))
    return random_str

def build_check_container(image_name: str, container_name: str):
    """Mock function - no actual Docker container needed"""
    bt.logging.info("Containerless mode - skipping Docker image build")
    return True

def build_sample_container():
    """Mock function - no Docker container needed"""
    bt.logging.info("Containerless mode - skipping sample container build")
    return {"status": True}

def check_container():
    """Check if allocation is active"""
    try:
        return os.path.exists(ACTIVE_ALLOCATION_FILE) and allocation_manager.ssh_daemon_pid is not None
    except:
        return False

def kill_container(deregister=False):
    """Clean up allocation"""
    try:
        allocation_manager.cleanup_allocation()

        if os.path.exists(ACTIVE_ALLOCATION_FILE):
            os.remove(ACTIVE_ALLOCATION_FILE)

        bt.logging.info("Allocation cleaned up successfully")

    except Exception as e:
        bt.logging.error(f"Error cleaning up allocation: {e}")

def run_container(cpu_usage, ram_usage, hard_disk_usage, gpu_usage, public_key, docker_requirement: dict, testing: bool):
    """Create allocation environment without Docker containers"""
    try:
        password = password_generator(10)

        docker_ssh_key = docker_requirement.get("ssh_key")
        docker_ssh_port = docker_requirement.get("ssh_port")
        external_user_port = docker_requirement.get("fixed_external_user_port")

        # Create work environment
        work_dir = allocation_manager.create_work_environment(docker_requirement)
        if not work_dir:
            return make_error_response("Failed to create work environment", status=False)

        allocation_manager.work_directory = work_dir

        # Setup SSH access
        if not allocation_manager.setup_ssh_daemon(docker_ssh_key, docker_ssh_port, work_dir, password):
            allocation_manager.cleanup_allocation()
            return make_error_response("Failed to setup SSH access", status=False)

        allocation_manager.ssh_port = docker_ssh_port

        # Create allocation info
        info = {
            "username": "root",
            "password": password,
            "port": docker_ssh_port,
            "fixed_external_user_port": external_user_port,
            "version": __version_as_int__
        }
        info_str = json.dumps(info)
        public_key_bytes = public_key.encode("utf-8")
        encrypted_info = rsa.encrypt_data(public_key_bytes, info_str)
        encrypted_info = base64.b64encode(encrypted_info).decode("utf-8")

        # Store allocation key
        file_path = 'allocation_key'
        allocation_key = base64.b64encode(public_key_bytes).decode("utf-8")

        with open(file_path, 'w') as file:
            file.write(allocation_key)

        # Mark allocation as active
        with open(ACTIVE_ALLOCATION_FILE, 'w') as f:
            f.write(str(allocation_manager.ssh_daemon_pid))

        return {
            "status": True,
            "info": encrypted_info,
            "message": "Allocation created successfully (containerless mode)"
        }

    except Exception as e:
        allocation_manager.cleanup_allocation()
        return make_error_response(f"Error creating allocation: {e}", status=False, exception=e)

def retrieve_allocation_key():
    try:
        file_path = 'allocation_key'
        with open(file_path, 'r') as file:
            allocation_key_encoded = file.read()
        allocation_key = base64.b64decode(allocation_key_encoded).decode('utf-8')
        return allocation_key
    except Exception as e:
        bt.logging.info("Error retrieving allocation key.")
        return None

def restart_container(public_key: str):
    """Restart allocation services"""
    try:
        allocation_key = retrieve_allocation_key()
        if allocation_key is None:
            return make_error_response("Failed to retrieve allocation key.", status=False)

        if allocation_key.strip() == public_key.strip():
            # Kill and restart SSH daemon
            if allocation_manager.ssh_daemon_pid:
                try:
                    os.kill(allocation_manager.ssh_daemon_pid, signal.SIGTERM)
                    time.sleep(2)
                except ProcessLookupError:
                    pass

            # Re-setup SSH daemon
            if allocation_manager.work_directory:
                docker_requirement = {"ssh_key": ""}  # Will need to be passed properly
                password = password_generator(10)

                if allocation_manager.setup_ssh_daemon("", allocation_manager.ssh_port, allocation_manager.work_directory, password):
                    return {"status": True, "message": "Allocation restarted successfully."}
                else:
                    return make_error_response("Failed to restart SSH daemon", status=False)
            else:
                return make_error_response("No active allocation to restart", status=False)
        else:
            return make_error_response("Permission denied.", status=False)

    except Exception as e:
        return make_error_response(f"Error restarting allocation: {e}", status=False, exception=e)

def pause_container(public_key: str):
    """Pause allocation (stop SSH daemon temporarily)"""
    try:
        allocation_key = retrieve_allocation_key()
        if allocation_key is None:
            return make_error_response("Failed to retrieve allocation key.", status=False)

        if allocation_key.strip() == public_key.strip():
            if allocation_manager.ssh_daemon_pid:
                try:
                    os.kill(allocation_manager.ssh_daemon_pid, signal.SIGSTOP)
                    return {"status": True, "message": "Allocation paused successfully."}
                except ProcessLookupError:
                    return make_error_response("No active allocation found", status=False)
            else:
                return make_error_response("No active allocation to pause", status=False)
        else:
            return make_error_response("Permission denied.", status=False)

    except Exception as e:
        return make_error_response(f"Error pausing allocation: {e}", status=False, exception=e)

def unpause_container(public_key: str):
    """Unpause allocation (resume SSH daemon)"""
    try:
        allocation_key = retrieve_allocation_key()
        if allocation_key is None:
            return make_error_response("Failed to retrieve allocation key.", status=False)

        if allocation_key.strip() == public_key.strip():
            if allocation_manager.ssh_daemon_pid:
                try:
                    os.kill(allocation_manager.ssh_daemon_pid, signal.SIGCONT)
                    return {"status": True, "message": "Allocation resumed successfully."}
                except ProcessLookupError:
                    return make_error_response("No active allocation found", status=False)
            else:
                return make_error_response("No active allocation to resume", status=False)
        else:
            return make_error_response("Permission denied.", status=False)

    except Exception as e:
        return make_error_response(f"Error resuming allocation: {e}", status=False, exception=e)

def exchange_key_container(new_ssh_key: str, public_key: str, key_type: str = "user"):
    """Update SSH key for allocation"""
    try:
        allocation_key = retrieve_allocation_key()
        if allocation_key is None:
            return make_error_response("Failed to retrieve allocation key.", status=False)

        if allocation_key.strip() == public_key.strip():
            if allocation_manager.work_directory:
                authorized_keys_file = os.path.join(allocation_manager.work_directory, ".ssh", "authorized_keys")

                # Read existing keys
                existing_keys = []
                if os.path.exists(authorized_keys_file):
                    with open(authorized_keys_file, "r") as f:
                        existing_keys = f.read().strip().split("\n")

                # Update based on key type
                if key_type == "user":
                    if len(existing_keys) == 0:
                        existing_keys = [new_ssh_key]
                    else:
                        existing_keys[0] = new_ssh_key
                elif key_type == "terminal":
                    if len(existing_keys) < 2:
                        existing_keys.append(new_ssh_key)
                    else:
                        existing_keys[1] = new_ssh_key
                else:
                    return make_error_response("Invalid key type", status=False)

                # Write updated keys
                with open(authorized_keys_file, "w") as f:
                    f.write("\n".join(filter(None, existing_keys)) + "\n")

                return {"status": True, "message": "SSH key updated successfully."}
            else:
                return make_error_response("No active allocation found", status=False)
        else:
            return make_error_response("Permission denied.", status=False)

    except Exception as e:
        return make_error_response(f"Error updating SSH key: {e}", status=False, exception=e)