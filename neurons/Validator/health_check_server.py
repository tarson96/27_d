#!/usr/bin/env python3
"""
Health Check Server Script

This script runs on the miner to provide an HTTP health check endpoint.
Uses PID file to prevent multiple instances and enable reliable process management.
"""

import http.server
import socketserver
import time
import sys
import argparse
import os
import signal


class HealthCheckHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for health check endpoint"""

    def do_GET(self):
        """Handle GET requests to the health check endpoint"""
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Health OK")
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_HEAD(self):
        """Handle HEAD requests (for health checks that don't need body)"""
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()

    def log_message(self, format, *args):
        """Override to use our custom logging format"""
        print(f"Health check server: {format % args}")


class TimeoutHTTPServer(socketserver.TCPServer):
    """HTTP server with timeout functionality"""

    def __init__(self, server_address, RequestHandlerClass, timeout=60, pid_file=None):
        self.timeout = timeout
        self.start_time = time.time()
        self.pid_file = pid_file
        super().__init__(server_address, RequestHandlerClass)
        self.allow_reuse_address = True

    def verify_request(self, request, client_address):
        """Check if we should continue accepting requests based on timeout"""
        if time.time() - self.start_time > self.timeout:
            print(f"Health check server: Timeout reached ({self.timeout}s) - stopping")
            return False
        return True

    def server_close(self):
        """Clean up PID file when server closes"""
        super().server_close()
        if self.pid_file and os.path.exists(self.pid_file):
            try:
                os.remove(self.pid_file)
                print(f"Health check server: PID file removed: {self.pid_file}")
            except OSError as e:
                print(f"Health check server: Error removing PID file: {e}")


def create_pid_file(pid_file_path):
    """
    Create PID file with current process ID.

    Args:
        pid_file_path (str): Path to PID file

    Returns:
        bool: True if PID file created successfully, False if already exists
    """
    try:
        # Check if PID file already exists
        if os.path.exists(pid_file_path):
            print(f"Health check server: PID file already exists: {pid_file_path}")
            return False

        # Write current PID to file
        with open(pid_file_path, 'w') as f:
            f.write(str(os.getpid()))

        print(f"Health check server: PID file created: {pid_file_path}")
        return True
    except Exception as e:
        print(f"Health check server: Error creating PID file: {e}")
        return False


def remove_pid_file(pid_file_path):
    """
    Remove PID file if it exists.

    Args:
        pid_file_path (str): Path to PID file
    """
    try:
        if os.path.exists(pid_file_path):
            os.remove(pid_file_path)
            print(f"Health check server: PID file removed: {pid_file_path}")
    except Exception as e:
        print(f"Health check server: Error removing PID file: {e}")


def signal_handler(signum, frame):
    """Handle termination signals gracefully"""
    print(f"Health check server: Received signal {signum}, shutting down gracefully")
    sys.exit(0)


def create_health_check_server(port=27015, timeout=60, host='0.0.0.0'):
    """
    Creates a HTTP server for health check.

    Args:
        port (int): Port to listen on
        timeout (int): Maximum wait time in seconds (default 60 seconds)
        host (str): Host to bind to (default '0.0.0.0' for all interfaces)
    """
    pid_file_path = f"/tmp/health_check_server_{port}.pid"

    try:
        print(f"Health check server: Starting on {host}:{port} (timeout: {timeout}s)", flush=True)

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        # Create PID file
        if not create_pid_file(pid_file_path):
            print(f"Health check server: Another instance is already running. Exiting.")
            sys.exit(1)

        # Create the server
        server = TimeoutHTTPServer((host, port), HealthCheckHandler, timeout, pid_file_path)

        print(f"Health check server: Ready - endpoint: /", flush=True)

        # Start the server
        server.serve_forever()

    except OSError as e:
        print(f"Health check server: Error - {e}", flush=True)
        if e.errno == 98:  # Address already in use
            print(f"Health check server: Port {port} is already in use", flush=True)
        elif e.errno == 13:  # Permission denied
            print(f"Health check server: Permission denied to bind to port {port}", flush=True)
        remove_pid_file(pid_file_path)
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"Health check server: Shutting down", flush=True)
    except Exception as e:
        print(f"Health check server: Unexpected error - {e}", flush=True)
        remove_pid_file(pid_file_path)
        sys.exit(1)
    finally:
        remove_pid_file(pid_file_path)
        if 'server' in locals():
            server.shutdown()
            server.server_close()


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Health Check HTTP Server')
    parser.add_argument('--port', type=int, default=27015,
                       help='Port for health check server (default: 27015)')
    parser.add_argument('--timeout', type=int, default=60,
                       help='Timeout in seconds for server (default: 60)')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                       help='Host to bind to (default: 0.0.0.0)')

    args = parser.parse_args()

    create_health_check_server(args.port, args.timeout, args.host)


if __name__ == "__main__":
    main()
