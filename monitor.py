"""
System monitoring module for gathering server information via SSH
"""
from typing import Dict, Optional
from ssh_client import SSHClient
import psutil
import platform
import subprocess
import socket


class ServerMonitor:
    """Collects system information from remote servers via SSH"""

    def __init__(self, host_config: Dict):
        """
        Initialize monitor with host configuration

        Args:
            host_config: Dictionary containing host connection info
        """
        self.name = host_config['name']
        self.ip = host_config['ip']
        self.port = host_config.get('ssh_port', 22)
        self.username = host_config['ssh_user']
        self.key_path = host_config.get('ssh_key_path')
        self.password = host_config.get('ssh_password')

    def get_system_info(self) -> Optional[Dict]:
        """
        Gather all system information from the remote host

        Returns:
            Dictionary with system info, or None if connection failed
        """
        ssh = SSHClient(self.ip, self.port, self.username, self.key_path, self.password)

        if not ssh.connect():
            return None

        try:
            info = {
                'hostname': self.name,
                'ip': self.ip,
                'cpu_model': self._get_cpu_model(ssh),
                'cpu_usage': self._get_cpu_usage(ssh),
                'ram_total': self._get_ram_total(ssh),
                'ram_used': self._get_ram_used(ssh),
                'disk_total': self._get_disk_total(ssh),
                'disk_usage': self._get_disk_usage(ssh),
                'process_count': self._get_process_count(ssh),
                'load_average': self._get_load_average(ssh),
                'online': True
            }
            return info

        finally:
            ssh.close()

    def _get_cpu_model(self, ssh: SSHClient) -> str:
        """Get CPU model name"""
        success, output = ssh.execute_command(
            "cat /proc/cpuinfo | grep 'model name' | head -1 | cut -d ':' -f 2 | xargs"
        )
        if success and output:
            return output.strip()
        return "Unknown"

    def _get_cpu_usage(self, ssh: SSHClient) -> str:
        """Get CPU usage percentage"""
        success, output = ssh.execute_command(
            "top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d '%' -f 1"
        )
        if success and output:
            try:
                usage = float(output.strip())
                return f"{usage:.1f}%"
            except ValueError:
                pass
        return "N/A"

    def _get_ram_total(self, ssh: SSHClient) -> str:
        """Get total RAM"""
        success, output = ssh.execute_command(
            "free -h | grep Mem | awk '{print $2}'"
        )
        if success and output:
            return output.strip()
        return "N/A"

    def _get_ram_used(self, ssh: SSHClient) -> str:
        """Get used RAM"""
        success, output = ssh.execute_command(
            "free -h | grep Mem | awk '{print $3}'"
        )
        if success and output:
            return output.strip()
        return "N/A"

    def _get_disk_total(self, ssh: SSHClient) -> str:
        """Get total disk space"""
        success, output = ssh.execute_command(
            "df -h / | tail -1 | awk '{print $2}'"
        )
        if success and output:
            return output.strip()
        return "N/A"

    def _get_disk_usage(self, ssh: SSHClient) -> str:
        """Get disk usage percentage"""
        success, output = ssh.execute_command(
            "df -h / | tail -1 | awk '{print $5}'"
        )
        if success and output:
            return output.strip()
        return "N/A"

    def _get_process_count(self, ssh: SSHClient) -> str:
        """Get number of running processes"""
        success, output = ssh.execute_command("ps aux | wc -l")
        if success and output:
            try:
                # Subtract 1 for the header line
                count = int(output.strip()) - 1
                return str(count)
            except ValueError:
                pass
        return "N/A"

    def _get_load_average(self, ssh: SSHClient) -> str:
        """Get 1-minute load average"""
        success, output = ssh.execute_command(
            "uptime | awk -F'load average:' '{print $2}' | awk -F',' '{print $1}' | xargs"
        )
        if success and output:
            return output.strip()
        return "N/A"

    def check_online(self) -> bool:
        """
        Check if host is online (can establish SSH connection)

        Returns:
            True if host is reachable, False otherwise
        """
        ssh = SSHClient(self.ip, self.port, self.username, self.key_path, self.password)
        result = ssh.connect()
        ssh.close()
        return result


class LocalMonitor:
    """Collects system information from the local machine using psutil"""

    def __init__(self):
        """Initialize local monitor"""
        self.name = f"{platform.node()} (localhost)"
        try:
            # Get local IP address
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            self.ip = s.getsockname()[0]
            s.close()
        except:
            self.ip = "127.0.0.1"

    def get_system_info(self) -> Optional[Dict]:
        """
        Gather all system information from the local machine

        Returns:
            Dictionary with system info
        """
        try:
            info = {
                'hostname': self.name,
                'ip': self.ip,
                'cpu_model': self._get_cpu_model(),
                'cpu_usage': self._get_cpu_usage(),
                'ram_total': self._get_ram_total(),
                'ram_used': self._get_ram_used(),
                'disk_total': self._get_disk_total(),
                'disk_usage': self._get_disk_usage(),
                'process_count': self._get_process_count(),
                'load_average': self._get_load_average(),
                'online': True
            }
            return info
        except Exception as e:
            print(f"Error gathering local system info: {e}")
            return None

    def _get_cpu_model(self) -> str:
        """Get CPU model name"""
        try:
            if platform.system() == "Darwin":  # macOS
                result = subprocess.run(
                    ['sysctl', '-n', 'machdep.cpu.brand_string'],
                    capture_output=True, text=True, timeout=5
                )
                return result.stdout.strip()
            elif platform.system() == "Linux":
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if 'model name' in line:
                            return line.split(':')[1].strip()
                return "Unknown CPU"
            else:
                return platform.processor()
        except:
            return "Unknown"

    def _get_cpu_usage(self) -> str:
        """Get CPU usage percentage"""
        try:
            usage = psutil.cpu_percent(interval=1)
            return f"{usage:.1f}%"
        except:
            return "N/A"

    def _get_ram_total(self) -> str:
        """Get total RAM"""
        try:
            total = psutil.virtual_memory().total
            return self._bytes_to_human(total)
        except:
            return "N/A"

    def _get_ram_used(self) -> str:
        """Get used RAM"""
        try:
            used = psutil.virtual_memory().used
            return self._bytes_to_human(used)
        except:
            return "N/A"

    def _get_disk_total(self) -> str:
        """Get total disk space"""
        try:
            total = psutil.disk_usage('/').total
            return self._bytes_to_human(total)
        except:
            return "N/A"

    def _get_disk_usage(self) -> str:
        """Get disk usage percentage"""
        try:
            usage = psutil.disk_usage('/').percent
            return f"{usage:.0f}%"
        except:
            return "N/A"

    def _get_process_count(self) -> str:
        """Get number of running processes"""
        try:
            count = len(psutil.pids())
            return str(count)
        except:
            return "N/A"

    def _get_load_average(self) -> str:
        """Get 1-minute load average"""
        try:
            if hasattr(psutil, 'getloadavg'):
                load = psutil.getloadavg()[0]
                return f"{load:.2f}"
            else:
                # Windows doesn't have load average
                return "N/A"
        except:
            return "N/A"

    def _bytes_to_human(self, bytes_val: int) -> str:
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.1f}{unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.1f}PB"

    def check_online(self) -> bool:
        """
        Check if localhost is online (always True)

        Returns:
            True
        """
        return True
