import plyer
import requests
import json
import datetime

send_os_notifications = False
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
    discord_tts = config_json["discord_tts"]
    discord_webhooks_json = config_json["discord_webhooks"]
    for disc_wh in discord_webhooks_json:
        discord_webhooks.append(DiscordWebhook(disc_wh["name"], disc_wh["username"], disc_wh["message"], disc_wh["avatar_url"], disc_wh["webhook_urls"]))

def send_os_notification(title, body):
    # Send OS notification using plyer package
    plyer.notification.notify(title, body)

def send_discord_webhook(title, body, fields, webhook_name):
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
                            "description": body,
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
            break
    

def notify(title, body, fields, webhook_name):
    print("\n[CONSOLE MESSAGE]")
    print(title)
    print(body)
    print("\n")

    send_discord_webhook(title, body, fields, webhook_name)
    send_os_notification(title, body)

def notify_error(title, body):
    print("\n[CONSOLE ERROR MESSAGE]")
    print(title)
    print(body)
    print("\n")

    send_os_notification(title, body)