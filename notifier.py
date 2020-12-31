import plyer
import requests
import json
import textwrap
import re

send_os_notifications = False
send_discord_messages = False
discord_tts = False
discord_webhooks = []

class DiscordWebhook:
    def __init__ (self, name, username, avatar_url, mention_prefix, webhook_urls):
        self.name = name
        self.username = username
        self.avatar_url = avatar_url
        self.mention_prefix = mention_prefix
        self.webhook_urls = webhook_urls

class NotificationCard:
    def __init__(self, title, description, fields):
        self.title = title
        self.description = description
        self.fields = fields

class Notification:
    def __init__ (self, title, cards, short_title, short_description):
        self.title = title
        self.cards = cards
        self.short_title = short_title
        self.short_description = short_description

with open("config/notifications.json") as config_file:
    config_json = json.load(config_file)
    send_os_notifications = config_json["send_os_notifications"]
    send_discord_messages = config_json["send_discord_messages"]
    discord_tts = config_json["discord_tts"]
    discord_webhooks_json = config_json["discord_webhooks"]
    for disc_wh in discord_webhooks_json:
        discord_webhooks.append(DiscordWebhook(disc_wh["name"], disc_wh["username"], disc_wh["avatar_url"], disc_wh["mention_prefix"], disc_wh["webhook_urls"]))

def validate_text(string, max_length):
    return textwrap.shorten(string, width=max_length, placeholder="...")

# Removes parts between : in a string
def remove_discord_emoji(string):
    return re.sub("\s*:[^:]*:\s*", "", string)

# Send an OS notification using the plyer package
def send_os_notification(notification, context_name):
    if not send_os_notifications:
        return
    title_short = validate_text(notification.short_title, 64)
    message_short = validate_text(notification.short_description, 64)
    plyer.notification.notify(title=title_short, message=message_short, app_name=context_name, app_icon="config/notification_icon.ico")

def send_discord_notification(notification, webhook_name):
    if not send_discord_messages:
        return
    for disc_wh in discord_webhooks:
        if disc_wh.name == webhook_name:
            for webhook_url in disc_wh.webhook_urls:
                username = disc_wh.username
                avatar = disc_wh.avatar_url
                
                embeds = []
                for card in notification.cards:
                    embed = {}
                    embed["color"] = 15158332
                    if card.title is not None:
                        embed["title"] = card.title
                    if card.description is not None:
                        embed["description"] = card.description
                    if card.fields is not None:
                        embed_fields = []
                        for name, value in card.fields.items():
                            embed_fields.append({
                                "name": name,
                                "value": value,
                                "inline": True,
                            })
                        embed["fields"] = embed_fields

                    embeds.append(embed)


                data = json.dumps({
                    "username": username,
                    "avatar_url": avatar,
                    "tts": discord_tts,
                    "content": disc_wh.mention_prefix + " " + notification.title,
                    "embeds": embeds
                })

                json_header = {
                    "content-type": "application/json"
                }

                response = requests.post(webhook_url, data, headers=json_header)

                if not response.ok:
                    print("Failed to execute discord wehook!")
                    print(response.status_code)
                    print(response.reason)
                    print(response.text)

def cards_to_string(cards):
    string = ""
    for card in cards:
        if card.title is not None and card.title is not "":
            string += card.title + "\n"
        if card.description is not None and card.description is not "":
            string += card.description + "\n"
        if card.fields is not None:
            for name, value in card.fields.items():
                string += str(name) + ": " + remove_discord_emoji(str(value)) + " "

    return string

def send_console_notification(notification, context_name):
    print("\n[" + remove_discord_emoji(notification.title) + "] (" + context_name + ")")
    message = cards_to_string(notification.cards)
    print(message)

def notify(notification, context):
    send_console_notification(notification, context)
    send_discord_notification(notification, context)
    send_os_notification(notification, context)

def notify_error(title, message):
    print("\n[CONSOLE ERROR MESSAGE]")
    print(title)
    print(message)