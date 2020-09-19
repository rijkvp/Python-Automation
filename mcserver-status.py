from mcstatus import MinecraftServer
from apscheduler.schedulers.blocking import BlockingScheduler
from plyer import notification
from threading import Thread
import json

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


def send_notification(title, body):
    notification.notify(title, body)


def ping_servers():
    for server_info in servers:
        server = MinecraftServer.lookup(server_info.ip)
        try:
            status = server.status()
        except:
            if server_info.is_online:
                send_notification("Server Offline", "The server {0} is no longer online!".format(
                    server_info.ip))
                server_info.is_online = False
            continue

        player_count = status.players.online
        ping = int(round(status.latency))

        if not server_info.is_online:
            send_notification("Server Online", "The server {0} is now online with {1} players! ({2} ms)".format(
                server_info.ip, player_count, ping))
            server_info.is_online = True
            server_info.player_count = player_count

        if player_count != server_info.player_count:
            diff = player_count - server_info.player_count
            if diff > 0:
                send_notification("Players Joined", "There is/are {0} player(s) online on {1} ({2} ms)".format(
                    player_count, server_info.ip, ping))
            elif diff < 0:
                send_notification("Players Left", "There is/are {0} player(s) online on {1} ({2} ms)".format(
                    player_count, server_info.ip, ping))
            server_info.player_count = player_count


if len(servers) > 0:
    scheduler = BlockingScheduler()
    scheduler.add_job(ping_servers, "interval", seconds=sync_delay)
    print("Pinging your minecraft servers every " +
          str(sync_delay) + " seconds..")
    scheduler.start()
else:
    print("Quitting - No servers defined in mc_servers.json.")
