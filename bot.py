"""
Discord bot for server monitoring
"""
import discord
from discord.ext import tasks
import asyncio
from typing import Dict, Optional
from config import Config
from monitor import ServerMonitor, LocalMonitor
from uptime_tracker import UptimeTracker


class MonitorBot(discord.Client):
    """Discord bot for monitoring multiple Ubuntu servers"""

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

        # Add localhost monitor
        self.local_monitor = LocalMonitor()

        # Add remote host monitors
        self.hosts = Config.load_hosts()
        self.monitors = {'localhost': self.local_monitor}
        self.monitors.update({host['name']: ServerMonitor(host) for host in self.hosts})

        self.uptime_tracker = UptimeTracker()
        self.message_ids = {}  # Store message IDs for each host

    async def on_ready(self):
        """Called when bot is ready"""
        print(f'Logged in as {self.user.name} ({self.user.id})')
        print('------')

        # Start background tasks
        self.update_status.start()
        self.check_uptime.start()

        # Initial status post
        await self.post_initial_status()

    async def post_initial_status(self):
        """Post initial status messages for all hosts"""
        channel = self.get_channel(int(Config.CHANNEL_ID))
        if not channel:
            print(f"Error: Could not find channel with ID {Config.CHANNEL_ID}")
            return

        for hostname in self.monitors.keys():
            embed = await self.create_status_embed(hostname)
            message = await channel.send(embed=embed)
            self.message_ids[hostname] = message.id

    async def create_status_embed(self, hostname: str) -> discord.Embed:
        """
        Create Discord embed with server status

        Args:
            hostname: Name of the host

        Returns:
            Discord Embed object
        """
        monitor = self.monitors[hostname]
        info = monitor.get_system_info()

        if info is None:
            # Host is offline
            embed = discord.Embed(
                title=f"🔴 {hostname}",
                description="**Host is OFFLINE**",
                color=discord.Color.red()
            )
            embed.add_field(name="IP", value=f"`{monitor.ip}`", inline=False)

            # Add uptime visualization
            uptime_emoji = self.uptime_tracker.get_uptime_emoji(hostname)
            embed.add_field(
                name="Uptime (48h)",
                value=uptime_emoji,
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

    @tasks.loop(seconds=Config.UPDATE_INTERVAL)
    async def update_status(self):
        """Periodically update status messages"""
        channel = self.get_channel(int(Config.CHANNEL_ID))
        if not channel:
            return

        for hostname, message_id in self.message_ids.items():
            try:
                message = await channel.fetch_message(message_id)
                embed = await self.create_status_embed(hostname)
                await message.edit(embed=embed)
            except discord.NotFound:
                # Message was deleted, create a new one
                embed = await self.create_status_embed(hostname)
                new_message = await channel.send(embed=embed)
                self.message_ids[hostname] = new_message.id
            except Exception as e:
                print(f"Error updating status for {hostname}: {e}")

    @tasks.loop(seconds=Config.UPTIME_CHECK_INTERVAL)
    async def check_uptime(self):
        """Periodically check and record uptime status"""
        for hostname, monitor in self.monitors.items():
            is_online = monitor.check_online()
            self.uptime_tracker.record_status(hostname, is_online)
            print(f"Uptime check: {hostname} - {'Online' if is_online else 'Offline'}")

        # Cleanup old records (keep last 7 days)
        deleted = self.uptime_tracker.cleanup_old_records(days=7)
        if deleted > 0:
            print(f"Cleaned up {deleted} old uptime records")

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
                    embed = await self.create_status_embed(hostname)
                    await message.channel.send(embed=embed)
            elif len(parts) == 2:
                # Show specific host
                hostname = parts[1]
                if hostname in self.monitors:
                    embed = await self.create_status_embed(hostname)
                    await message.channel.send(embed=embed)
                else:
                    await message.channel.send(f"Host `{hostname}` not found")

        elif message.content.startswith('!uptime'):
            parts = message.content.split()
            if len(parts) == 2:
                hostname = parts[1]
                if hostname in self.monitors:
                    uptime_emoji = self.uptime_tracker.get_uptime_emoji(hostname)
                    embed = discord.Embed(
                        title=f"Uptime History: {hostname}",
                        description=f"Past 48 hours:\n{uptime_emoji}",
                        color=discord.Color.blue()
                    )
                    await message.channel.send(embed=embed)
                else:
                    await message.channel.send(f"Host `{hostname}` not found")


def main():
    """Main entry point"""
    # Validate configuration
    if not Config.validate():
        print("Configuration validation failed. Please check your .env and hosts.json files.")
        return

    # Create and run bot
    bot = MonitorBot()
    bot.run(Config.DISCORD_TOKEN)


if __name__ == '__main__':
    main()
