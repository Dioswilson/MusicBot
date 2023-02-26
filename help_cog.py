import asyncio
from discord.ext import commands


class help_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_message = """
```
General commands:
""" + bot.command_prefix + """help - displays all the available commands
""" + bot.command_prefix + """p <keywords> - finds the song on youtube and plays it in your current channel. Will resume playing the current song if it was paused
""" + bot.command_prefix + """q - displays the current music queue
""" + bot.command_prefix + """skip    - skips the current song being played
""" + bot.command_prefix + """clear   - Stops the music and clears the queue
""" + bot.command_prefix + """leave   - Disconnected the bot from the voice channel
""" + bot.command_prefix + """join    - Joins the bot into a voice channel, continues reproducing if it has any left
""" + bot.command_prefix + """pause   - pauses the current song being played or resumes if already paused
""" + bot.command_prefix + """resume  - resumes playing the current song
""" + bot.command_prefix + """shuffle - shuffles music queue
```
"""

    # some debug info so that we know the bot has started
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'Logged in as {self.bot.user}.')

    @commands.command(name="help", help="Displays all the available commands")
    async def help(self, ctx):
        message = await ctx.send(self.help_message)
        await asyncio.sleep(120)  # wait for 2 minutes (120 seconds)
        await message.delete()
        await ctx.message.delete()
