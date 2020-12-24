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

## Config files

To make the scripts work you need to provide some information config files:

**TODO:** Add config info
