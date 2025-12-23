"""
Configuration manager for the Discord monitoring bot
"""
import os
import json
import logging
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    """Configuration class for bot settings"""

    # Discord settings
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    CHANNEL_ID = os.getenv('CHANNEL_ID')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    # Update intervals (in seconds)
    UPDATE_INTERVAL = int(os.getenv('UPDATE_INTERVAL', 60))
    UPTIME_CHECK_INTERVAL = int(os.getenv('UPTIME_CHECK_INTERVAL', 3600))
    UPDATE_SPREAD_SECONDS = float(os.getenv('UPDATE_SPREAD_SECONDS', 0.5))

    # Database
    DB_PATH = 'uptime_history.db'
    MESSAGE_IDS_FILE = 'message_ids.json'

    # Hosts configuration file
    HOSTS_FILE = 'hosts.json'

    # Networking
    LOCAL_INTERFACE = os.getenv('LOCAL_INTERFACE', '')

    # SSH security
    STRICT_HOST_KEY_CHECKING = os.getenv('STRICT_HOST_KEY_CHECKING', 'false').lower() in ('1', 'true', 'yes')
    KNOWN_HOSTS_FILE = os.getenv('KNOWN_HOSTS_FILE', '')

    @staticmethod
    def load_hosts() -> List[Dict]:
        """Load host configurations from JSON file"""
        try:
            with open(Config.HOSTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                hosts = data.get('hosts', [])
                return Config._validate_hosts(hosts)
        except FileNotFoundError:
            logger.error("Hosts file not found: %s", Config.HOSTS_FILE)
            return []
        except json.JSONDecodeError as e:
            logger.error("Error parsing %s: %s", Config.HOSTS_FILE, e)
            return []

    @staticmethod
    def _validate_hosts(hosts: List[Dict]) -> List[Dict]:
        """Validate host entries and drop invalid ones."""
        valid_hosts = []
        seen_names = set()
        for host in hosts:
            name = host.get('name')
            ip = host.get('ip')
            user = host.get('ssh_user')
            key_path = host.get('ssh_key_path')
            password = host.get('ssh_password')
            if not name or not ip or not user:
                logger.warning("Skipping host with missing required fields: %s", host)
                continue
            if name in seen_names:
                logger.warning("Skipping duplicate host name: %s", name)
                continue
            if not key_path and not password:
                logger.warning("Skipping host without ssh_key_path or ssh_password: %s", name)
                continue
            seen_names.add(name)
            valid_hosts.append(host)
        return valid_hosts

    @staticmethod
    def validate() -> bool:
        """Validate required configuration"""
        if not Config.DISCORD_TOKEN:
            logger.error("DISCORD_TOKEN not set in .env")
            return False

        if not Config.CHANNEL_ID:
            logger.error("CHANNEL_ID not set in .env")
            return False

        # hosts.json can be empty - localhost is always monitored
        hosts = Config.load_hosts()
        if not hosts:
            logger.info("No remote hosts configured in hosts.json. Only localhost will be monitored.")

        return True
