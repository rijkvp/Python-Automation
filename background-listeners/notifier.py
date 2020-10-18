import plyer
import requests
import json
import datetime
import textwrap

send_os_notifications = False
send_discord_messages = False
discord_tts = False
discord_webhooks = []

class DiscordWebhook:
    def __init__ (self, name, username, message, avatar_url, webhook_urls):
        self.name = name
        self.username = username
        self.message = message
        self.avatar_url = avatar_url
        self.webhook_urls = webhook_urls

with open("config/notification_settings.json") as config_file:
    config_json = json.load(config_file)
    send_os_notifications = config_json["send_os_notifications"]
    send_discord_messages = config_json["send_discord_messages"]
    discord_tts = config_json["discord_tts"]
    discord_webhooks_json = config_json["discord_webhooks"]
    for disc_wh in discord_webhooks_json:
        discord_webhooks.append(DiscordWebhook(disc_wh["name"], disc_wh["username"], disc_wh["message"], disc_wh["avatar_url"], disc_wh["webhook_urls"]))

def validate_text(string, max_length):
    return textwrap.shorten(string, width=max_length, placeholder="...")

# Send an OS notification using plyer package
def send_os_notification(title, message, context_name):
    if not send_os_notifications:
        return
    title_short = validate_text(title, 64)
    message_short = validate_text(message, 64)
    plyer.notification.notify(title=title_short, message=message_short, app_name=context_name, app_icon="config/notification_icon.ico")

def send_discord_message(title, fields, webhook_name):
    if not send_discord_messages:
        return
    for disc_wh in discord_webhooks:
        if disc_wh.name == webhook_name:
            for webhook_url in disc_wh.webhook_urls:
                username = disc_wh.username
                avatar = disc_wh.avatar_url
                timestamp = datetime.datetime.now().isoformat()
                
                embed_fields = []
                for name, value in fields.items():
                    embed_fields.append({
                        "name": name,
                        "value": value,
                        "inline": True,
                    })

                data = json.dumps({
                    "username": username,
                    "avatar_url": avatar,
                    "tts": discord_tts,
                    "content": disc_wh.message,
                    "embeds": [
                        {
                            "title": title,
                            "fields": embed_fields,
                            "color": 15158332,
                            "timestamp": timestamp
                        }
                    ]
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

def fields_to_sring(fields):
    string = ""
    for name, value in fields.items():
        string += str(name) + ": " + str(value)
    return string

def notify(title, fields, context_name):
    print("\n[CONSOLE MESSAGE]")
    print(title)
    message = fields_to_sring(fields)
    print(message)

    send_discord_message(title, fields, context_name)
    send_os_notification(title, message, context_name)

def notify_error(title, message):
    print("\n[CONSOLE ERROR MESSAGE]")
    print(title)
    print(message)

    send_os_notification(title, message, "Error")