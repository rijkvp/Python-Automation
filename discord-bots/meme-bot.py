import discord
from discord.ext import commands
import re
import json
import random
import datetime
import asyncio
import os

# Gobals
client_secret = None
onwer_ids = None
bot_prefix = None
memes = []

ffmpeg_executable = None

with open("config/config.json", "r") as f:
    config_json = json.loads(f.read())
    client_secret = config_json["secret"]
    onwer_ids = [int(id) for id in config_json["onwer_ids"]] 
    bot_prefix = config_json["bot_prefix"]
    ffmpeg_executable = config_json["ffmpeg_executable"]

class Meme:
    def __init__(self, triggers, images):
        self.triggers = triggers
        self.images = images

    def as_dict(self):
        return {
            "triggers": list([t.lower() for t in self.triggers]), # Ensure lowercase
            "images": list(self.images)
        }

def load_memes():
    with open("config/memes.json", "r") as f:
        memes_json = json.loads(f.read())
        for meme in memes_json:
            memes.append(Meme([t.lower() for t in meme["triggers"]], meme["images"]))

def save_memes():
    memes_dict = [m.as_dict() for m in memes]
    memes_json = json.dumps(memes_dict, indent=4)
    with open("config/memes.json", "w") as f:
        f.write(memes_json)

load_memes()

def word_in_list(words, word_list):
    for word in words:
        if word in word_list:
            return True
    return False

def list_to_string(string_list):
    return ', '.join(string_list)

def load_sounds_folder(folder_name):
    path = os.path.join(os.getcwd(), "config" + os.path.sep + "sounds" + os.path.sep + folder_name) 
    paths = []
    for folder, subs, files in os.walk(path):
        for filename in files:
            paths.append(os.path.abspath(os.path.join(folder, filename)))
    return paths

def get_random_sound(array):
    return random.choice(array)

start_sounds = load_sounds_folder("start")
song_start_sounds = load_sounds_folder("song_start")
song_sounds = load_sounds_folder("songs")
end_sounds = load_sounds_folder("end")

intents = discord.Intents.all()
bot = commands.Bot(intents=intents, command_prefix=bot_prefix, help_command=None)

@bot.command()
async def say(ctx, *, text):
    if ctx.message.author.id in onwer_ids:
        await ctx.message.delete()
        await ctx.send(text)
    else:
        username = ctx.message.author.mention
        await ctx.message.delete(delay=5)
        await ctx.send("Ik luister alleen naar mijn eigenaar, {}!".format(username), delete_after=5)

@bot.command(name="play")
async def play(ctx, song):
    try:
        await ctx.message.delete()
    except:
        pass
    await ctx.send("Ik houd niet van het liedje {}, {}!".format(song, ctx.message.author.mention))

@bot.command(name="join")
async def join(ctx):
    if ctx.message.author.id in onwer_ids:
        await ctx.message.delete()
        await ctx.send("Trying to join the voice channel of {}...".format(ctx.message.author), delete_after=5)
        user_found = False
        for guild in bot.guilds:
            if guild.get_member(ctx.message.author.id) is not None:
                for voice_channel in guild.voice_channels:
                    if ctx.message.author in voice_channel.members:
                        user_found = True
                        print("[Joining voice channel] Server: {}, Channel: {}, Members: {}".format(guild.name, voice_channel.name, len(voice_channel.members)))
                        voice_client = await voice_channel.connect()

                        voice_client.play(discord.FFmpegPCMAudio(source=get_random_sound(start_sounds), executable=ffmpeg_executable, before_options="-nostdin"))
                        await asyncio.sleep(4)
                        voice_client.play(discord.FFmpegPCMAudio(source=get_random_sound(song_start_sounds), executable=ffmpeg_executable, before_options="-nostdin"))
                        await asyncio.sleep(6)
                        voice_client.play(discord.FFmpegPCMAudio(source=get_random_sound(song_sounds), executable=ffmpeg_executable, before_options="-nostdin"))
                        await asyncio.sleep(10)
                        voice_client.play(discord.FFmpegPCMAudio(source=get_random_sound(end_sounds), executable=ffmpeg_executable, before_options="-nostdin"))
                        await asyncio.sleep(5)

                        await voice_client.disconnect()
        if not user_found:
            await ctx.send("Couldn't find {} in one of the voice channels of my servers!".format(ctx.message.author), delete_after=5)
    else:
        username = ctx.message.author.mention
        await ctx.message.delete(delay=5)
        await ctx.send("Ik luister alleen naar mijn eigenaar, {}!".format(username), delete_after=5)

@bot.command(name="clear-memes")
async def clear_memes(ctx, limit):
    if ctx.message.author.id in onwer_ids:
        await ctx.message.delete()
        counter = 0
        async for msg in ctx.message.channel.history():
            if msg.author == bot.user:
                await msg.delete()
                counter += 1
                if counter >= int(limit):
                    break
    else:
        await ctx.message.delete(delay=5)
        await ctx.send("Ik luister alleen naar mijn eigenaar, {}!".format(ctx.message.author.mention), delete_after=5)

@bot.command(name="add-meme")
async def add_meme(ctx, trigger, new_meme):
    if ctx.message.author.id in onwer_ids:
        for meme in memes:
            for t in meme.triggers: 
                if trigger == t.lower():
                    if not new_meme in meme.images:
                        meme.images.append(new_meme)
                        save_memes()
                        await ctx.send("{}, ik heb een nieuwe meme toegevoegd aan de triggers: {}".format(ctx.message.author.mention, list_to_string(meme.triggers)))
                    else:
                        await ctx.send("{}, die meme is al toegevoegd! Triggers: {}".format(ctx.message.author.mention, list_to_string(meme.triggers)))
                    return
    else:
        await ctx.message.delete(delay=5)
        await ctx.send("Ik luister alleen naar mijn eigenaar, {}!".format(ctx.message.author.mention), delete_after=5)

@bot.command(name="add-trigger")
async def add_trigger(ctx, existing_trigger, new_trigger):
    if ctx.message.author.id in onwer_ids:
        for meme in memes:
            for t in meme.triggers: 
                if existing_trigger == t.lower():
                    if not new_trigger in meme.triggers:
                        meme.triggers.append(new_trigger)
                        save_memes()
                        await ctx.send("{}, de trigger {} is toegevoegd aan de triggers: {}".format(ctx.message.author.mention, new_trigger, list_to_string(meme.triggers)))
                    else:
                        await ctx.send("{}, de trigger {} is al toegevoegd! Triggers: {}".format(ctx.message.author.mention, new_trigger, list_to_string(meme.triggers)))
                    return
    else:
        await ctx.message.delete(delay=5)
        await ctx.send("Ik luister alleen naar mijn eigenaar, {}!".format(ctx.message.author.mention), delete_after=5)

@bot.command(name="add-triggers")
async def add_triggers(ctx, *args):
    if ctx.message.author.id in onwer_ids:
        new_triggers = [a.lower() for a in args]
        found = False
        for meme in memes:
            for t in new_triggers:
                if t in meme.triggers:
                    found = True
        if not found:
            memes.append(Meme(new_triggers, []))
            save_memes()
            await ctx.send("{}, de triggers '{}' zijn toegevoegd!".format(ctx.message.author.mention, list_to_string(new_triggers)))
        else:
            await ctx.send("{}, een of meerdere van de triggers '{}' zijn al toegevoegd aan een bestaande meme!".format(ctx.message.author.mention, list_to_string(new_triggers)))
        
    else:
        await ctx.message.delete(delay=5)
        await ctx.send("Ik luister alleen naar mijn eigenaar, {}!".format(ctx.message.author.mention), delete_after=5)

@bot.command(name="help")
async def help(ctx):
    if ctx.message.author.id in onwer_ids:
        await ctx.send("Waar kan ik u mee van dienst zijn?\n*(Ik luister btw alleen naar mijn eigenaren)*\n\n**Commando's:**\nGebruik de prefix: '`{}`'\n`add-meme [trigger] [new-meme]` voeg een nieuw plaatje toe aan een bestaande meme\n`add-trigger [existing-trigger] [new-trigger]` voeg een nieuwe trigger toe aan een bestaande meme\n`add-triggers [trigger] ..` voeg een nieuwe en lege meme toe met triggers".format(bot_prefix))
    else:
        await ctx.message.delete(delay=5)
        await ctx.send("Ik help jou niet, {}!! Ik luister alleen naar mijn eigeaar!".format(ctx.message.author.mention), delete_after=5)

@bot.command()
async def ping(ctx):
    if ctx.message.author.id in onwer_ids:
        await ctx.send('Pong! {0}ms'.format(round(bot.latency * 1000)))
    else:
        await ctx.message.delete(delay=5)
        await ctx.send("Ik luister alleen naar mijn eigenaar, {}!".format(ctx.message.author.mention), delete_after=5)

@bot.event
async def on_ready():
    print('Logged in as: {0.user}'.format(bot))
    start_activity = discord.Activity(name='Memes aan het chappen..', type=discord.ActivityType.custom)
    await bot.change_presence(activity=start_activity)

async def send_meme(message):
    words = re.split(r'[ :?!(),.&;]+', message.content.lower())

    for word in words:
        for meme in memes:
            for trigger in meme.triggers: 
                if word == trigger.lower():
                    meme = random.choice(meme.images)
                    print("[MEME] Detected word '{}' in '{}' from {} -> sending meme '{}'".format(word, message.content, str(message.author), meme))
                    await message.channel.send(meme)
                    return # Prevent spam!

@bot.event
async def on_message(message):
    await bot.process_commands(message)

    if message.author == bot.user:
        return
    if message.content.startswith(bot_prefix):
        return

    await send_meme(message)
    
bot.run(client_secret)