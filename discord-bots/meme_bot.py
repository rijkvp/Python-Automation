import discord
import re
import json
import random

client_secret = None
with open("config/credentials.json", "r") as f:
    credentials_json = json.loads(f.read())
    client_secret = credentials_json["secret"]

class Meme:
    def __init__(self, triggers, images):
        self.triggers = triggers
        self.images = images

memes = []

with open("config/memes.json", "r") as f:
    memes_json = json.loads(f.read())
    for meme in memes_json:
        memes.append(Meme(meme["triggers"], meme["images"]))

client = discord.Client()

@client.event
async def on_ready():
    print('Logged in as: {0.user}'.format(client))

def word_in_list(words, word_list):
    for word in words:
        if word in word_list:
            return True
    return False

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    words = re.split(r'[ :?!(),.&;]+', message.content.lower())

    for word in words:
        for meme in memes:
            for trigger in meme.triggers: 
                if word == trigger.lower():
                    meme = random.choice(meme.images)
                    print("[MEME] Detected word '{}' in '{}' from {} -> sending meme '{}'".format(word, message.content, str(message.author), meme));
                    await message.channel.send(meme)
                    break

client.run(client_secret)