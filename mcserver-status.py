from mcstatus import MinecraftServer
from apscheduler.schedulers.blocking import BlockingScheduler
from plyer import notification
from threading import Thread
import json
import notifier

sync_delay = 30

with open('config/settings.json') as settings_file:
    settings_json = json.load(settings_file)
    sync_delay = int(settings_json["sync_delay"])


class ServerInfo:
    def __init__(self, ip):
        self.ip = ip
        self.is_online = False
        self.player_count = 0


servers = []

with open('config/mc_servers.json') as config_file:
    servers_json = json.load(config_file)
    for server_ip in servers_json:
        servers.append(ServerInfo(server_ip))


def send_notification(title, fields):
    notifier.notify(title, fields, "Minecraft")

def ping_servers():
    for server_info in servers:
        server = MinecraftServer.lookup(server_info.ip)
        try:
            status = server.status()
        except:
            if server_info.is_online:
                notification_fields = {
                    "IP": server_info.ip,
                    "Status": "Offline"
                }
                send_notification(server_info.ip + " is offline", notification_fields)
                server_info.is_online = False
            continue

        player_count = status.players.online
        ping = int(round(status.latency))

        if not server_info.is_online:
            notification_fields = {
                "IP": server_info.ip,
                "Status": "Online",
                "Players": server_info.player_count,
                "Ping": ping
            }
            send_notification(server_info.ip + " is online", notification_fields)
            server_info.is_online = True
            server_info.player_count = player_count

        if player_count != server_info.player_count:
            diff = player_count - server_info.player_count
            notification_fields = {
                "IP": server_info.ip,
                "Status": "Online",
                "Players": server_info.player_count,
                "Ping": ping
            }
            if diff > 0:
                send_notification("Player(s) joined", notification_fields)
            elif diff < 0:
                send_notification("Player(s) left", notification_fields)
            server_info.player_count = player_count


if len(servers) > 0:
    scheduler = BlockingScheduler()
    scheduler.add_job(ping_servers, "interval", seconds=sync_delay)
    print("Pinging your minecraft servers every " +
          str(sync_delay) + " seconds..")
    scheduler.start()
else:
    print("Quitting - No servers defined in mc_servers.json.")
