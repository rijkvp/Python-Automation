from mcstatus import MinecraftServer
from apscheduler.schedulers.blocking import BlockingScheduler
from plyer import notification
import json
import notifier

sync_interval = 30

with open('config/settings.json') as settings_file:
    settings_json = json.load(settings_file)
    sync_interval = int(settings_json["sync_interval"])

class ServerInfo:
    def __init__(self, ip, name):
        self.ip = ip
        self.name = name
        self.is_online = False
        self.player_count = 0


servers = []

with open('config/mc_servers.json') as config_file:
    servers_json = json.load(config_file)
    for server_name, server_ip in servers_json.items():
        servers.append(ServerInfo(server_ip, server_name))


def ping_servers():
    for server_info in servers:
        server = MinecraftServer.lookup(server_info.ip)
        status = None
        try:
            status = server.status()
        except:
            server_info.is_online = False

        if status is not None:
            player_count = status.players.online
            max_players = status.players.max
            ping = int(round(status.latency))
            player_info = "{}/{}".format(player_count, max_players)
            player_names = None
            if status.players.sample is not None:
                player_names = [s.name for s in status.players.sample]
            if player_names is not None and len(player_names) == 0:
                player_names = None

            server_version = status.version.name

            notification_fields = {
                "IP": server_info.ip,
                "Status": "Online",
                "Online": player_info,
                "Ping": str(ping) + "ms",
                "Versie": server_version
            }
            if player_names is not None:
                notification_fields["Spelers"] = ", ".join(player_names)

            if not server_info.is_online and player_count > 0:
                if player_count == 1:
                    if player_names is not None:
                        title = "{} is online met {}".format(
                            server_info.name, ", ".join(player_names))
                    else:
                        title = "{} is online met {} speler!".format(
                            server_info.name, player_count)
                else:
                    title = "{} is online met {} spelers!".format(
                        server_info.name, player_count)
                short_desc = "{}ms - {} - {}".format(
                    ping, server_info.ip, server_version)
                if player_names is not None:
                    short_desc += " - " + ",".join(player_names)
                notifier.notify(notifier.Notification(title, [notifier.NotificationCard(
                    "Info", "", notification_fields)], title, short_desc), "Minecraft")

            if player_count != server_info.player_count and server_info.is_online:
                diff = player_count - server_info.player_count

                if diff != 0:
                    short_desc = "{} -  {}ms - {}".format(player_info,
                                                                                      ping, server_info.ip, server_version)
                    if player_names is not None:
                        short_desc += " - " + ",".join(player_names)
                    title = None
                    if player_count == 0:
                        title = "Niemand meer online op {} :(".format(
                            server_info.name)
                    elif diff > 0:
                        if diff == 1:
                            title = "{} speler is {} gejoined!".format(
                                abs(diff), server_info.name)
                        else:
                            title = "{} spelers zijn {} gejoined!".format(
                                abs(diff), server_info.name)
                    elif diff < 0:
                        if diff == -1:
                            title = "{} speler is {} geleaved!".format(
                                abs(diff), server_info.name)
                        else:
                            title = "{} spelers zijn {} geleaved!".format(
                                abs(diff), server_info.name)

                    notifier.notify(notifier.Notification(title, [notifier.NotificationCard(
                        "Info", "", notification_fields)], title, short_desc), "Minecraft")
            server_info.is_online = True
            server_info.player_count = player_count


if len(servers) > 0:
    ping_servers()
    scheduler = BlockingScheduler()
    scheduler.add_job(ping_servers, "interval", seconds=sync_interval)
    print("Pinging your minecraft servers every " +
          str(sync_interval) + " seconds..")
    scheduler.start()
else:
    print("Quitting - No servers defined in mc_servers.json.")
