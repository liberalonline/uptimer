"""
Uptime history tracker using SQLite database
"""
import logging
import sqlite3
import time
from typing import List, Tuple

from config import Config

logger = logging.getLogger(__name__)


class UptimeTracker:
    """Manages uptime history in SQLite database"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DB_PATH
        self._init_db()

    def _init_db(self):
        """Initialize database and create tables if not exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS uptime_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hostname TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                status INTEGER NOT NULL,
                UNIQUE(hostname, timestamp)
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_hostname_timestamp
            ON uptime_history(hostname, timestamp)
        ''')

        conn.commit()
        conn.close()

    def record_status(self, hostname: str, status: bool):
        """
        Record uptime status for a host

        Args:
            hostname: Host name
            status: True if host is up, False if down
        """
        # Round to the nearest hour
        current_time = int(time.time())
        hour_timestamp = (current_time // 3600) * 3600

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO uptime_history (hostname, timestamp, status)
                VALUES (?, ?, ?)
            ''', (hostname, hour_timestamp, 1 if status else 0))
            conn.commit()
        except sqlite3.Error as e:
            logger.error("Database error: %s", e)
        finally:
            conn.close()

    def get_history(self, hostname: str, hours: int = 48) -> List[Tuple[int, int]]:
        """
        Get uptime history for the last N hours

        Args:
            hostname: Host name
            hours: Number of hours to retrieve (default: 48)

        Returns:
            List of (timestamp, status) tuples
        """
        current_time = int(time.time())
        start_time = current_time - (hours * 3600)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT timestamp, status
            FROM uptime_history
            WHERE hostname = ? AND timestamp >= ?
            ORDER BY timestamp ASC
        ''', (hostname, start_time))

        results = cursor.fetchall()
        conn.close()

        return results

    def get_uptime_emoji(self, hostname: str, hours: int = 48) -> str:
        """
        Generate uptime visualization using emojis

        Args:
            hostname: Host name
            hours: Number of hours to display (default: 48)

        Returns:
            String of emojis representing uptime status, or empty string if no data
        """
        history = self.get_history(hostname, hours)

        # Return empty string if no data
        if not history:
            return ""

        # Create a dictionary for quick lookup
        history_dict = {ts: status for ts, status in history}

        # Generate emoji string for the last 48 hours
        current_time = int(time.time())
        emoji_string = ""
        unknown_emoji = "⬜"

        for i in range(hours):
            # Calculate timestamp for this hour (from oldest to newest)
            hour_offset = hours - i - 1
            hour_timestamp = ((current_time - (hour_offset * 3600)) // 3600) * 3600

            if hour_timestamp in history_dict:
                # We have data for this hour
                status = history_dict[hour_timestamp]
                emoji_string += "🟩" if status == 1 else "🟥"
            else:
                # No data for this specific hour - treat as unknown
                emoji_string += unknown_emoji

        return emoji_string

    def cleanup_old_records(self, days: int = 7):
        """
        Remove records older than specified days

        Args:
            days: Number of days to keep (default: 7)
        """
        cutoff_time = int(time.time()) - (days * 24 * 3600)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            DELETE FROM uptime_history
            WHERE timestamp < ?
        ''', (cutoff_time,))

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted_count
