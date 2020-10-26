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
        data_response = requests.get(
            "https://api.thevirustracker.com/free-api?countryTotal=NL")
        if data_response.ok:
            data_json = data_response.json()

            with open("data/covid19_data.json", "w+") as f:
                f.write(json.dumps(data_json, indent=4))

            date_str = datetime.date.today().strftime("%Y-%m-%d")

            new_cases = data_json["countrydata"][0]["total_new_cases_today"]
            new_deaths = data_json["countrydata"][0]["total_new_deaths_today"]

            fields = {
                "Nieuwe besmettingen": f'{new_cases:n}',
                "Nieuwe doden": f'{new_deaths:n}' + " :skull_crossbones:",
                "Datum": today.strftime('%x'),
            }

            notifier.notify(
                f'{new_cases:n}' + " nieuwe COVID-19 besmettingen", fields, "covid19-updates")

            update_dates.append(today)

            dates_json = json.dumps([d.strftime("%Y-%m-%d") for d in update_dates])
            with open("data/covid19_update_dates.json", "w+") as f:
                f.write(dates_json)

scheduler = BlockingScheduler()
scheduler.add_job(get_updates, "interval", seconds=200)
print("Starting scheduler..")
scheduler.start()
