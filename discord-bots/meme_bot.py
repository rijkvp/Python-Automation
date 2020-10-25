import discord
import re
import json
import random

class Meme:
    def __init__(self, triggers, images):
        self.triggers = triggers
        self.images = images

memes = []

with open("memes.json", "r") as f:
    memes_json = json.loads(f.read())
    for meme in memes_json:
        memes.append(Meme(meme["triggers"], meme["images"]))

client = discord.Client()

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

def word_in_list(words, word_list):
    for word in words:
        if word in word_list:
            return True
    return False

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    print("Message: '" + message.content + "' from " + str(message.author))
    
    words = re.split(r'[ :?!(),.&;]+', message.content.lower())

    for word in words:
        for meme in memes:
            if word in meme.triggers:
                await message.channel.send(random.choice(meme.images))

client.run("secret")