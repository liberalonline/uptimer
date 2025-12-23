"""
SSH client for remote command execution
"""
import logging
import os
from typing import Optional, Tuple
import paramiko

logger = logging.getLogger(__name__)


class SSHClient:
    """SSH client wrapper for executing remote commands"""

    def __init__(
        self,
        hostname: str,
        port: int,
        username: str,
        key_path: str = None,
        password: str = None,
        known_hosts_file: str = None,
        strict_host_key_checking: bool = False
    ):
        """
        Initialize SSH client

        Args:
            hostname: Remote host IP or hostname
            port: SSH port (default: 22)
            username: SSH username
            key_path: Path to SSH private key (optional)
            password: SSH password (optional, used if key_path is not provided)
        """
        self.hostname = hostname
        self.port = port
        self.username = username
        self.key_path = os.path.expanduser(key_path) if key_path else None
        self.password = password
        self.client = None
        self.known_hosts_file = os.path.expanduser(known_hosts_file) if known_hosts_file else None
        self.strict_host_key_checking = strict_host_key_checking
        self.last_error: Optional[str] = None

    def connect(self) -> bool:
        """
        Establish SSH connection

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.last_error = None
            self.client = paramiko.SSHClient()
            if self.known_hosts_file:
                self.client.load_host_keys(self.known_hosts_file)
            else:
                self.client.load_system_host_keys()

            if self.strict_host_key_checking:
                self.client.set_missing_host_key_policy(paramiko.RejectPolicy())
            else:
                self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Use key-based authentication if key_path is provided
            if self.key_path:
                # Try to load the private key
                private_key = None
                try:
                    private_key = paramiko.RSAKey.from_private_key_file(self.key_path)
                except:
                    # Try Ed25519 key
                    try:
                        private_key = paramiko.Ed25519Key.from_private_key_file(self.key_path)
                    except:
                        logger.error("Failed to load SSH key from %s", self.key_path)
                        self.last_error = f"Failed to load SSH key from {self.key_path}"
                        return False

                self.client.connect(
                    hostname=self.hostname,
                    port=self.port,
                    username=self.username,
                    pkey=private_key,
                    timeout=10,
                    banner_timeout=10
                )
            # Use password authentication if password is provided
            elif self.password:
                self.client.connect(
                    hostname=self.hostname,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    timeout=10,
                    banner_timeout=10
                )
            else:
                logger.error("No authentication method provided (key_path or password)")
                self.last_error = "No authentication method provided (key_path or password)"
                return False

            return True

        except paramiko.AuthenticationException:
            logger.error("Authentication failed for %s@%s", self.username, self.hostname)
            self.last_error = "Authentication failed"
            return False
        except paramiko.SSHException as e:
            logger.error("SSH error connecting to %s: %s", self.hostname, e)
            self.last_error = str(e)
            return False
        except Exception as e:
            logger.error("Error connecting to %s: %s", self.hostname, e)
            self.last_error = str(e)
            return False

    def execute_command(self, command: str) -> Tuple[bool, str]:
        """
        Execute a command on the remote host

        Args:
            command: Command to execute

        Returns:
            Tuple of (success: bool, output: str)
        """
        if not self.client:
            self.last_error = "Not connected"
            return False, "Not connected"

        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=10)
            exit_status = stdout.channel.recv_exit_status()
            output = stdout.read().decode('utf-8').strip()
            error = stderr.read().decode('utf-8').strip()

            if exit_status != 0:
                self.last_error = error or output or f"Exit status {exit_status}"
                return False, error or output or f"Exit status {exit_status}"

            self.last_error = None
            return True, output if output else error

        except Exception as e:
            self.last_error = str(e)
            return False, str(e)

    def close(self):
        """Close SSH connection"""
        if self.client:
            self.client.close()
            self.client = None

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
