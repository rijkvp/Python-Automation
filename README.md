# Python-Automation

A bundle of python scripts that run on the background and notify me about updates of different websites/Apps/APIs.

![Lines of code](https://img.shields.io/tokei/lines/github/rijkvp/Python-Automation?style=for-the-badge)

## Notifications

`notifier.py` will send notifications in 3 different ways:

- Console output.
- OS Notifications using the [plyer](https://pypi.org/project/plyer/) package.
- Discord Webhooks.

All of those options are configurable with a json file.

## Scripts

- `zermelo-listener.py`

Notifies about schedule updates. Many schools in the Netherlands are using [Zermelo](https://www.zermelo.nl/) as their schedule software.

- `somtoday-listener.py`

Notifies about new homework & grades in [Somtoday](https://som.today/). Somtoday is a student information system for secondary education.

- `mcserver-status.py`

Notifies you about minecraft server status changes. Handy if your friends are manually hosting their servers and you want to know when they are online.

## Dependencies

These are all python packages from [PyPI](https://pypi.org):

- requests
- apscheduler
- html2text
- mcstatus
- plyer

## Config files

To make the scripts work you need to provide some information andn credentials in the config files. The files need to be placed in the `/config` folder.

`config/settigns.json`

Some general information needed by all scripts. Currently it only has the sync interval setting. This is the interval in which the scripts should synchronize.

```js
{
    "sync_interval": "100"
}
```

`config/notifications.json`

Use this file to configure your notifications. It gets used by `notifier.py` and so by all scripts:

```js
{
    "send_os_notifications": true,
    "send_discord_messages": true, 
    "discord_tts": false,
    "discord_webhooks": [ // Optional
        {
            "name": "-", // Choose between: Zermelo, Somtoday-Grades, Somtoday-Homework
            "username": "My Awesome Webhook", // The username in Discord
            "avatar_url": "-",
            "mention_prefix": "<@&[role id here]>", // Copy the id of the role in Discord 
            "webhook_urls": [""] // Copy the URL of the webhook in Discord
        }
    ]
}
```

`config/zermelo-credentials.json`

To make the Zermelo listener work go to the 'Koppel App' page on the zermelo portal. Copy the orginization abbreviation and the one-time auth code and pase them in the file. Also provide the abbreviation or id's of the groups you want to receive the schedule from:

```js
{
    "organization": "**",
    "auth_code": "",
    "group_names": [""],
    "group_ids": [] // Optional
}
```

`config/somtoday-credentials.json`

This file is needed for the Somtoday listener. It should contain the same credentials used to login to the somtoday website:

```js
{
    "school_name": "Name of your school",
    "username": "your username",
    "password": "your password"
}
```

`config/mc-servers.json`

A list of the IP-addesses for the servers the Minecraft server status script uses. Use the following syntax:

```js
[
    "example.com",
    "example-with-port.com:25565",
    "subdomain.domain.co.uk"
]
```

`config/subjects.json` & `config/teachers.json`

**Optional:** These files contain the abbreviations of subjects and teachers with their coresponding names. They are used by the Zermelo & Somtoday listeners. You can use this to make your notifications more readable. If a name isn't specified the  abbreviation will be used instead:

```js
{
    "abbreviation": "full name"
}
```

`config/notification_icon.ico`

**Optional:** A icon used for the OS-notifications by the `plyer` package.
