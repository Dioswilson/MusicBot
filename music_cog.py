import asyncio
import functools
import typing
from random import shuffle

import discord
from discord.ext import commands
from yt_dlp import YoutubeDL


class music_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # all the music related stuff
        self.is_playing: bool = False
        self.is_paused: bool = False
        self.currently_playing: str = ""

        # 2d array containing [song, channel]
        self.music_queue: list[[dict, object]] = []
        self.YDL_OPTIONS: dict = {'format': 'bestaudio/best',
                                  'ignoreerrors': 'True',
                                  'geo_bypass': 'True',
                                  'lazy_playlist': "True",
                                  "playlist_items": "1",
                                  "nocheckcertificate": True,
                                  "extract_flat": True,
                                  }
        self.FFMPEG_OPTIONS: dict = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                                     'options': '-vn'}
        self.vc = None

    # searching the item on YouTube
    def search_yt(self, item: str):
        with YoutubeDL(self.YDL_OPTIONS) as ydl:
            try:
                if not item.startswith("https://"):
                    info = ydl.extract_info("ytsearch1:%s" % item, download=False)['entries'][0]  # [:1]
                elif "list=" in item:
                    if "&list=" in item:
                        info = ydl.extract_info(item.split("&list=")[0], download=False)
                    else:
                        info = ydl.extract_info(item, download=False)['entries'][0]  # Playlist (Only first item)
                else:
                    info = ydl.extract_info(item, download=False)
            except Exception as e:
                print(e.__class__)
                return False

            if info is not None:
                # if 'format_note' in video_format:
                #     if video_format['format_note'] == "medium":
                #         final_format = video_format
                #         break
                # else:
                #     final_format = info['formats'][0]
                # return {'source': final_format['url'], 'title': info['title']}
                return {'source': info["url"], 'title': info['title']}
            else:
                return False

    def add_playlist_items(self, playlist_url: str, voice_chat):
        new_opts: dict = self.YDL_OPTIONS
        new_opts["playlist_items"] = "2:"
        info = YoutubeDL(new_opts).extract_info(playlist_url, download=False)
        for entry in info["entries"]:
            self.music_queue.append([{"source": entry["url"], "title": entry["title"]}, voice_chat])

    async def play_next(self, ctx):
        if self.is_playing:
            if len(self.music_queue) > 0:

                # get the first url
                m_url: str = self.music_queue[0][0]['source']
                self.currently_playing = self.music_queue[0][0]['title']

                is_valid_song: bool = False
                while not is_valid_song:
                    # remove the first element as you are currently playing it
                    self.music_queue.pop(0)
                    if m_url.startswith("https://www.youtube"):
                        song = await self.run_blocking(self.search_yt, m_url)
                        if not isinstance(song, bool):
                            m_url = song["source"]
                            is_valid_song = True
                        else:
                            m_url: str = self.music_queue[0][0]['source']
                            self.currently_playing = self.music_queue[0][0]['title']
                    else:
                        is_valid_song = True

                self.vc.play(discord.FFmpegPCMAudio(m_url, **self.FFMPEG_OPTIONS),
                             after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop))
            else:
                await ctx.send("Finished reproducing songs")
                self.is_playing = False

    async def play_music(self, ctx):
        if len(self.music_queue) > 0:
            self.is_playing = True

            m_url: str = self.music_queue[0][0]['source']
            self.currently_playing = self.music_queue[0][0]['title']

            # try to connect to voice channel if you are not already connected
            if self.vc is None or not self.vc.is_connected():
                self.vc = await self.music_queue[0][1].connect()

                # in case we fail to connect
                if self.vc is None:
                    await ctx.send("Could not connect to the voice channel")
                    return
            else:
                await self.vc.move_to(self.music_queue[0][1])

            is_valid_song: bool = False
            while not is_valid_song:
                # remove the first element as you are currently playing it
                self.music_queue.pop(0)
                if m_url.startswith("https://www.youtube"):
                    song = await self.run_blocking(self.search_yt, m_url)
                    if not isinstance(song, bool):
                        m_url = song["source"]
                        is_valid_song = True
                    else:
                        m_url: str = self.music_queue[0][0]['source']
                        self.currently_playing = self.music_queue[0][0]['title']
                else:
                    is_valid_song = True

            self.vc.play(discord.FFmpegPCMAudio(m_url, **self.FFMPEG_OPTIONS),
                         after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop))
        else:
            await ctx.send("Finished reproducing songs")
            self.is_playing = False

    async def run_blocking(self, blocking_func: typing.Callable, *args, **kwargs) -> typing.Any:
        """Runs a blocking function in a non-blocking way"""
        func = functools.partial(blocking_func,
                                 *args, )  # `run_in_executor` doesn't support kwargs, `functools.partial` does
        return await self.bot.loop.run_in_executor(None, func)

    @commands.command(name="play", aliases=["p", "playing", "Play", "PLAY"], help="Plays a selected song from youtube")
    async def play_command(self, ctx, *args):
        query = " ".join(args)

        try:
            voice_channel = ctx.author.voice.channel
        except AttributeError:
            await ctx.send("Connect to a voice channel!")
        else:
            if self.is_paused:
                self.vc.resume()
            else:

                await ctx.send("Searching song")
                song = await self.run_blocking(self.search_yt, query)  # If playlist only adds first song

                if isinstance(song, bool):
                    await ctx.send(
                        "Could not download the song. Video deleted/private/geo restricted or incorrect searching format")
                else:
                    self.music_queue.append([song, voice_channel])
                    if "playlist" in query:
                        old_size = len(self.music_queue) - 1
                        await self.run_blocking(self.add_playlist_items, query, voice_channel)
                        await ctx.send("Added " + str(len(self.music_queue) - old_size) + " songs to queue")
                    else:
                        await ctx.send("Song added to the queue")

                    if not self.is_playing:
                        await self.play_music(ctx)

    @commands.command(name="pause", aliases=["Pause", "PAUSE"], help="Pauses the current song being played")
    async def pause(self, ctx, *args):
        if self.is_playing:
            self.is_playing = False
            self.is_paused = True
            self.vc.pause()
            message = await ctx.send("Song paused")
            await asyncio.sleep(3)
            await message.delete()
        elif self.is_paused:
            self.is_paused = False
            self.is_playing = True
            self.vc.resume()
            message = await ctx.send("Song resumed")
            await asyncio.sleep(3)
            await message.delete()

    @commands.command(name="resume", aliases=["r", "Resume", "RESUME"], help="Resumes playing with the discord bot")
    async def resume(self, ctx, *args):
        if self.is_paused:
            self.is_paused = False
            self.is_playing = True
            self.vc.resume()
            message = ctx.send("Song resumed")
            await asyncio.sleep(3)
            await message.delete()

    @commands.command(name="skip", aliases=["s", "Skip", "SKIP"], help="Skips the current song being played")
    async def skip(self, ctx, *args: str):
        if self.vc is not None and self.vc:
            self.currently_playing = ""
            amount: int = 1
            if len(args) == 1:
                if args[0].isdigit():
                    amount = int(args[0])

            del self.music_queue[:amount - 1]
            self.vc.stop()
            await ctx.send("Skipped " + str(amount) + " songs")

    @commands.command(name="queue", aliases=["q", "Queue", "QUEUE"], help="Displays the current songs in queue")
    async def queue(self, ctx):
        retval = "Currently playing: " + self.currently_playing + "\n" + str(
            len(self.music_queue)) + " songs in queue. Displaying first " + (
                     "5" if len(self.music_queue) > 5 else str(len(self.music_queue))) + ": \n"
        for i in range(0, len(self.music_queue)):
            # display a max of 5 songs in the current queue
            if i > 4:
                break
            retval += self.music_queue[i][0]['title'] + "\n"

        await ctx.send(retval)

    @commands.command(name="clear", aliases=["c", "bin", "Clear", "CLEAR"], help="Stops the music and clears the queue")
    async def clear(self, ctx):
        self.music_queue = []
        await ctx.send("Music queue cleared")

    @commands.command(name="leave", aliases=["stop", "disconnect", "quit", "l", "d", "Leave", "LEAVE"],
                      help="Kick the bot from VC")
    async def leave(self, ctx):
        self.is_playing = False
        self.is_paused = False
        await self.vc.disconnect()
        message = await ctx.send("Disconnected from voice")
        await asyncio.sleep(3)
        await message.delete()

    @commands.command(name="join", aliases=["j", "connect", "Join", "JOIN"],
                      help="Joins the bot into a voice channel, continues reproducing if it has any left")
    async def join(self, ctx):
        try:
            if len(self.music_queue) > 0:
                voice_channel = self.music_queue[0][1]
            else:
                voice_channel = ctx.author.voice.channel

            if self.vc is None or not self.vc.is_connected():
                self.vc = await voice_channel.connect()

                # in case we fail to connect
                if self.vc is None:
                    await ctx.send("Could not connect to the voice channel")
                    return
            else:
                await self.vc.move_to(voice_channel)
            if self.currently_playing:
                song = await self.run_blocking(self.search_yt, self.currently_playing)
                self.music_queue.insert(0, [song, voice_channel])
                await self.play_music(ctx)
                await ctx.send("Joined to a voice channel")
            else:
                await ctx.send("Joined to a voice channel with no music to play")
                self.currently_playing = ""

        except AttributeError:
            await ctx.send("Connect to a voice channel!")

    @commands.command(name="shuffle", aliases=["mix", "Shuffle", "SHUFFLE"],
                      help="Shuffles music queue")
    async def shuffle(self, ctx):
        shuffle(self.music_queue)
        await ctx.send("Queue shuffled")
