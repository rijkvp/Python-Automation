from mcstatus import MinecraftServer
from apscheduler.schedulers.blocking import BlockingScheduler
from plyer import notification
from threading import Thread
import json

pingInterval = 30

with open('config/settings.json') as settingsFile:
    settingsJson = json.load(settingsFile)
    pingInterval = int(settingsJson["sync_delay"])


class ServerInfo:
    def __init__(self, ip):
        self.ip = ip
        self.isOnline = False
        self.playerCount = 0


servers = []

with open('config/mc_servers.json') as configFile:
    serversJson = json.load(configFile)
    for serverIp in serversJson:
        servers.append(ServerInfo(serverIp))


def send_notification(title, body):
    notification.notify(title, body)


def ping_servers():
    for serverInfo in servers:
        server = MinecraftServer.lookup(serverInfo.ip)
        try:
            status = server.status()
        except:
            if serverInfo.isOnline:
                send_notification("Server Offline", "The server {0} is no longer online!".format(
                    serverInfo.ip))
                serverInfo.isOnline = False
            continue

        playerCount = status.players.online
        ping = int(round(status.latency))

        if not serverInfo.isOnline:
            send_notification("Server Online", "The server {0} is now online with {1} players! ({2} ms)".format(
                serverInfo.ip, playerCount, ping))
            serverInfo.isOnline = True
            serverInfo.playerCount = playerCount

        if playerCount != serverInfo.playerCount:
            diff = playerCount - serverInfo.playerCount
            if diff > 0:
                send_notification("Players Joined", "There is/are {0} player(s) online on {1} ({2} ms)".format(
                    playerCount, serverInfo.ip, ping))
            elif diff < 0:
                send_notification("Players Left", "There is/are {0} player(s) online on {1} ({2} ms)".format(
                    playerCount, serverInfo.ip, ping))
            serverInfo.playerCount = playerCount


if len(servers) > 0:
    scheduler = BlockingScheduler()
    scheduler.add_job(ping_servers, "interval", seconds=pingInterval)
    print("Pinging your minecraft servers every " +
          str(pingInterval) + " seconds..")
    scheduler.start()
else:
    print("Quitting - No servers defined in mc_servers.json.")
