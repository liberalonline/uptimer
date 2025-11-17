"""
SSH client for remote command execution
"""
import paramiko
import os
from typing import Optional, Tuple


class SSHClient:
    """SSH client wrapper for executing remote commands"""

    def __init__(self, hostname: str, port: int, username: str, key_path: str = None, password: str = None):
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

    def connect(self) -> bool:
        """
        Establish SSH connection

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.client = paramiko.SSHClient()
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
                        print(f"Failed to load SSH key from {self.key_path}")
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
                print("No authentication method provided (key_path or password)")
                return False

            return True

        except paramiko.AuthenticationException:
            print(f"Authentication failed for {self.username}@{self.hostname}")
            return False
        except paramiko.SSHException as e:
            print(f"SSH error connecting to {self.hostname}: {e}")
            return False
        except Exception as e:
            print(f"Error connecting to {self.hostname}: {e}")
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
            return False, "Not connected"

        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=10)
            output = stdout.read().decode('utf-8').strip()
            error = stderr.read().decode('utf-8').strip()

            if error:
                return False, error

            return True, output

        except Exception as e:
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
