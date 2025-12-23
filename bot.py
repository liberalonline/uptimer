"""
Discord bot for server monitoring
"""
import asyncio
import json
import logging
import time
from typing import Dict, Optional

import discord
from discord.ext import tasks

from config import Config
from monitor import ServerMonitor, LocalMonitor
from uptime_tracker import UptimeTracker

logger = logging.getLogger(__name__)


class MonitorBot(discord.Client):
    """Discord bot for monitoring multiple Ubuntu servers"""

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

        # Add localhost monitor
        # Add remote host monitors
        self.hosts = Config.load_hosts()
        self.monitors = {}
        for host in self.hosts:
            if host.get('ip') in ('localhost', '127.0.0.1'):
                self.monitors[host['name']] = LocalMonitor(name_override=host['name'])
            else:
                self.monitors[host['name']] = ServerMonitor(host)

        self.uptime_tracker = UptimeTracker()
        self.message_ids = self._load_message_ids()
        self.message_ids = {host: msg_id for host, msg_id in self.message_ids.items() if host in self.monitors}
        self.status_cache = {}

    async def on_ready(self):
        """Called when bot is ready"""
        logger.info("Logged in as %s (%s)", self.user.name, self.user.id)

        # Start background tasks
        self.update_status.start()
        self.check_uptime.start()

        # Initial status post
        await self.post_initial_status()

    async def post_initial_status(self):
        """Post initial status messages for all hosts"""
        channel = self.get_channel(int(Config.CHANNEL_ID))
        if not channel:
            logger.error("Could not find channel with ID %s", Config.CHANNEL_ID)
            return

        for hostname in self.monitors.keys():
            message_id = self.message_ids.get(hostname)
            embed = await self.create_status_embed(hostname, refresh=True)
            if message_id:
                try:
                    message = await channel.fetch_message(message_id)
                    await message.edit(embed=embed)
                    continue
                except discord.NotFound:
                    pass
                except Exception as e:
                    logger.warning("Failed to fetch existing message for %s: %s", hostname, e)
            message = await channel.send(embed=embed)
            self.message_ids[hostname] = message.id
        self._save_message_ids()

    async def create_status_embed(self, hostname: str, refresh: bool = False) -> discord.Embed:
        """
        Create Discord embed with server status

        Args:
            hostname: Name of the host

        Returns:
            Discord Embed object
        """
        info = await self._get_status(hostname, refresh=refresh)

        if info is None:
            # Host is offline
            embed = discord.Embed(
                title=f"🔴 {hostname}",
                description="**Host is OFFLINE**",
                color=discord.Color.red()
            )
            embed.add_field(name="IP", value=f"`{self.monitors[hostname].ip}`", inline=False)
            error_detail = getattr(self.monitors[hostname], "last_error", None)
            if error_detail:
                embed.add_field(name="Error", value=f"`{error_detail}`", inline=False)

            # Add uptime visualization
            uptime_emoji = self.uptime_tracker.get_uptime_emoji(hostname)
            embed.add_field(
                name="Uptime (48h)",
                value=uptime_emoji or "No data yet",
                inline=False
            )
            return embed

        # Host is online - create detailed embed
        embed = discord.Embed(
            title=f"🟢 {hostname}",
            color=discord.Color.green()
        )

        # Basic info
        embed.add_field(name="Host", value=f"`{info['hostname']}`", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # Spacing
        embed.add_field(name="IP", value=f"`{info['ip']}`", inline=True)

        # CPU info
        embed.add_field(
            name="📊 CPU",
            value=f"`{info['cpu_model']}`",
            inline=True
        )
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # Spacing
        embed.add_field(
            name="Usage",
            value=f"`{info['cpu_usage']}`",
            inline=True
        )

        # RAM info
        embed.add_field(
            name="💾 RAM",
            value=f"`{info['ram_total']}`",
            inline=True
        )
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # Spacing
        embed.add_field(
            name="Used",
            value=f"`{info['ram_used']}`",
            inline=True
        )

        # Disk info
        embed.add_field(
            name="💿 Disk",
            value=f"`{info['disk_total']}`",
            inline=True
        )
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # Spacing
        embed.add_field(
            name="Usage",
            value=f"`{info['disk_usage']}`",
            inline=True
        )

        # Process and load
        embed.add_field(
            name="🔄 Processes",
            value=f"`{info['process_count']}`",
            inline=True
        )
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # Spacing
        embed.add_field(
            name="Load Avg",
            value=f"`{info['load_average']}`",
            inline=True
        )

        # Uptime visualization
        uptime_emoji = self.uptime_tracker.get_uptime_emoji(hostname)
        if uptime_emoji:  # Only show if there's data
            embed.add_field(
                name="Uptime (48h)",
                value=uptime_emoji,
                inline=False
            )

        embed.set_footer(text="Last updated")
        embed.timestamp = discord.utils.utcnow()

        return embed

    async def _get_status(self, hostname: str, refresh: bool = False) -> Optional[Dict]:
        cached = self.status_cache.get(hostname)
        now = time.time()
        if cached and not refresh and (now - cached["timestamp"] < Config.UPDATE_INTERVAL):
            return cached["info"]
        monitor = self.monitors[hostname]
        info = await asyncio.to_thread(monitor.get_system_info)
        self.status_cache[hostname] = {"info": info, "timestamp": now}
        return info

    @tasks.loop(seconds=Config.UPDATE_INTERVAL)
    async def update_status(self):
        """Periodically update status messages"""
        channel = self.get_channel(int(Config.CHANNEL_ID))
        if not channel:
            return

        tasks = []
        for index, (hostname, message_id) in enumerate(self.message_ids.items()):
            tasks.append(self._update_host_message(channel, hostname, message_id, index))
        await asyncio.gather(*tasks)
        self._save_message_ids()

    async def _update_host_message(self, channel, hostname: str, message_id: int, index: int):
        await asyncio.sleep(index * Config.UPDATE_SPREAD_SECONDS)
        try:
            message = await channel.fetch_message(message_id)
            embed = await self.create_status_embed(hostname, refresh=True)
            await message.edit(embed=embed)
        except discord.NotFound:
            embed = await self.create_status_embed(hostname, refresh=True)
            new_message = await channel.send(embed=embed)
            self.message_ids[hostname] = new_message.id
        except Exception as e:
            logger.warning("Error updating status for %s: %s", hostname, e)

    @tasks.loop(seconds=Config.UPTIME_CHECK_INTERVAL)
    async def check_uptime(self):
        """Periodically check and record uptime status"""
        tasks = []
        for index, (hostname, monitor) in enumerate(self.monitors.items()):
            tasks.append(self._check_single_uptime(hostname, monitor, index))
        await asyncio.gather(*tasks)

        # Cleanup old records (keep last 7 days)
        deleted = self.uptime_tracker.cleanup_old_records(days=7)
        if deleted > 0:
            logger.info("Cleaned up %s old uptime records", deleted)

    @update_status.before_loop
    async def before_update_status(self):
        """Wait until bot is ready before starting update loop"""
        await self.wait_until_ready()

    @check_uptime.before_loop
    async def before_check_uptime(self):
        """Wait until bot is ready before starting uptime check loop"""
        await self.wait_until_ready()

    async def on_message(self, message):
        """Handle incoming messages"""
        # Ignore messages from the bot itself
        if message.author == self.user:
            return

        # Simple command handling
        if message.content.startswith('!status'):
            parts = message.content.split()
            if len(parts) == 1:
                # Show all hosts
                for hostname in self.monitors.keys():
                    embed = await self.create_status_embed(hostname, refresh=True)
                    await message.channel.send(embed=embed)
            elif len(parts) == 2:
                # Show specific host
                hostname = parts[1]
                if hostname in self.monitors:
                    embed = await self.create_status_embed(hostname, refresh=True)
                    await message.channel.send(embed=embed)
                else:
                    await message.channel.send(f"Host `{hostname}` not found")
            else:
                await message.channel.send("Usage: `!status [hostname]`")

        elif message.content.startswith('!uptime'):
            parts = message.content.split()
            if len(parts) == 2:
                hostname = parts[1]
                if hostname in self.monitors:
                    uptime_emoji = self.uptime_tracker.get_uptime_emoji(hostname)
                    embed = discord.Embed(
                        title=f"Uptime History: {hostname}",
                        description=f"Past 48 hours:\n{uptime_emoji or 'No data yet'}",
                        color=discord.Color.blue()
                    )
                    await message.channel.send(embed=embed)
                else:
                    await message.channel.send(f"Host `{hostname}` not found")
            else:
                await message.channel.send("Usage: `!uptime <hostname>`")

    async def _check_single_uptime(self, hostname: str, monitor, index: int):
        await asyncio.sleep(index * Config.UPDATE_SPREAD_SECONDS)
        is_online = await asyncio.to_thread(monitor.check_online)
        self.uptime_tracker.record_status(hostname, is_online)
        logger.info("Uptime check: %s - %s", hostname, "Online" if is_online else "Offline")

    def _load_message_ids(self) -> Dict[str, int]:
        try:
            with open(Config.MESSAGE_IDS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {k: int(v) for k, v in data.items()}
        except FileNotFoundError:
            return {}
        except Exception as e:
            logger.warning("Failed to load message IDs: %s", e)
            return {}

    def _save_message_ids(self):
        try:
            with open(Config.MESSAGE_IDS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.message_ids, f, ensure_ascii=True, indent=2)
        except Exception as e:
            logger.warning("Failed to save message IDs: %s", e)


def main():
    """Main entry point"""
    logging.basicConfig(
        level=Config.LOG_LEVEL,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    # Validate configuration
    if not Config.validate():
        logger.error("Configuration validation failed. Please check your .env and hosts.json files.")
        return

    # Create and run bot
    bot = MonitorBot()
    bot.run(Config.DISCORD_TOKEN)


if __name__ == '__main__':
    main()
