import requests
import json
import os
import notifier
import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
import locale

locale.setlocale(locale.LC_ALL, '')
os.makedirs("data", exist_ok=True)

update_dates = []
if os.path.exists("data/covid19_update_dates.json"):
    with open("data/covid19_update_dates.json") as f:
        update_dates_json = json.loads(f.read())
        for date_json in update_dates_json:
            date = datetime.datetime.strptime(date_json, "%Y-%m-%d").date()
            update_dates.append(date)


def get_updates():
    today = datetime.date.today()
    hour = datetime.datetime.now().hour
    if today not in update_dates and hour >= 14:

            fields = {
                "Datum": today.strftime('%x'),
            }

            notifier.notify("Het weer een dag met corona vandaag. De API werkt niet meer dus geen niews.", fields, "covid19-updates")

            update_dates.append(today)

            dates_json = json.dumps([d.strftime("%Y-%m-%d") for d in update_dates])
            with open("data/covid19_update_dates.json", "w+") as f:
                f.write(dates_json)

get_updates()
scheduler = BlockingScheduler()
scheduler.add_job(get_updates, "interval", seconds=200)
print("Starting scheduler..")
scheduler.start()
