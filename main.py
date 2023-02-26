import asyncio
import discord
from discord.ext import commands

# import all the cogs
from help_cog import help_cog
from music_cog import music_cog

# Change the prefix here if you want
client = commands.Bot(command_prefix='!', intents=discord.Intents.all())

client.remove_command('help')


async def main():
    await client.add_cog(help_cog(client))
    await client.add_cog(music_cog(client))


if __name__ == '__main__':
    asyncio.run(main())
# start the bot with your token
client.run('DISCORD TOKEN')
