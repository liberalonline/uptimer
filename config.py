"""
Configuration manager for the Discord monitoring bot
"""
import os
import json
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration class for bot settings"""

    # Discord settings
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    CHANNEL_ID = os.getenv('CHANNEL_ID')

    # Update intervals (in seconds)
    UPDATE_INTERVAL = int(os.getenv('UPDATE_INTERVAL', 60))
    UPTIME_CHECK_INTERVAL = int(os.getenv('UPTIME_CHECK_INTERVAL', 3600))

    # Database
    DB_PATH = 'uptime_history.db'

    # Hosts configuration file
    HOSTS_FILE = 'hosts.json'

    @staticmethod
    def load_hosts() -> List[Dict]:
        """Load host configurations from JSON file"""
        try:
            with open(Config.HOSTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('hosts', [])
        except FileNotFoundError:
            print(f"Error: {Config.HOSTS_FILE} not found")
            return []
        except json.JSONDecodeError as e:
            print(f"Error parsing {Config.HOSTS_FILE}: {e}")
            return []

    @staticmethod
    def validate() -> bool:
        """Validate required configuration"""
        if not Config.DISCORD_TOKEN:
            print("Error: DISCORD_TOKEN not set in .env")
            return False

        if not Config.CHANNEL_ID:
            print("Error: CHANNEL_ID not set in .env")
            return False

        # hosts.json can be empty - localhost is always monitored
        hosts = Config.load_hosts()
        if not hosts:
            print("Info: No remote hosts configured in hosts.json. Only localhost will be monitored.")

        return True
