from apscheduler.schedulers.blocking import BlockingScheduler
import requests
import json
from datetime import datetime, timedelta
import os
import re
from enum import Enum
import notifier
import html2text

BASE_URL = "https://production.somtoday.nl"

sync_interval = 30
with open('config/settings.json') as settings_file:
    settings_json = json.load(settings_file)
    sync_interval = int(settings_json["sync_interval"])

# Subject names
with open('config/subjects.json') as file:
    subject_dict = json.loads(file.read())

# Credentials
school_name = None
username = None
password = None


def load_credentials():
    global school_name
    global username
    global password
    with open("config/somtoday_credentials.json", "r") as config_file:
        config_json = json.loads(config_file.read())
        school_name = config_json["school_name"]
        username = config_json["username"]
        password = config_json["password"]


# Get the uuid with the school name
school_uuid = None


def get_school_uuid():
    global school_uuid
    org_request = requests.get("https://servers.somtoday.nl/organisaties.json")
    org_list = json.loads(org_request.text)

    for org in org_list[0]["instellingen"]:
        if org["naam"] == school_name:
            school_uuid = org["uuid"]
            break


# Authentication
access_token = None
refresh_token = None
endpoint = None
access_header = None


def authenticate():
    global access_token
    global endpoint
    global access_header
    global refresh_token
    is_authenticated = access_token is not None
    data = {"grant_type": "password",
            "username": school_uuid + "\\" + username,
            "password": password,
            "scope": "openid"}
    acces_headers = {
        "Authorization": "Basic RDUwRTBDMDYtMzJEMS00QjQxLUExMzctQTlBODUwQzg5MkMyOnZEZFdkS3dQTmFQQ3loQ0RoYUNuTmV5ZHlMeFNHTkpY", "Accept": "application/json"}

    if access_token == None:
        token_request = requests.post(
            BASE_URL + "/oauth2/token", data=data, headers=acces_headers)
        print("STATUS: " + str(token_request.status_code))
        if token_request.status_code == 500:
            print("SomToday internal server error!")
            quit()
        elif token_request.status_code == 200:
            token_json = json.loads(token_request.text)

            access_token = token_json["access_token"]
            refresh_token = token_json["refresh_token"]
            endpoint = token_json["somtoday_api_url"]
            access_header = {"Authorization": "Bearer " +
                             access_token, "Accept": "application/json"}
            is_authenticated = True
        else:
            is_authenticated = False
    if refresh_token != None and not is_authenticated:
        print("Refreshing the token..")
        data = {"grant_type": "refresh_token",
                "refresh_token": refresh_token}
        refresh_request = requests.post(
            BASE_URL + "/oauth2/token", data=data, headers=acces_headers)
        token_json = json.loads(refresh_request.text)

        access_token = token_json["access_token"]
        refresh_token = token_json["refresh_token"]
        endpoint = token_json["somtoday_api_url"]
        access_header = {"Authorization": "Bearer " +
                         access_token, "Accept": "application/json"}
        is_authenticated = True
    if is_authenticated == False:
        print("Couldnt get the acces token!")


def read_json_file(filePath):
    if (os.path.isfile(filePath)):
        readFile = open(filePath)
        fileData = readFile.read()
        readFile.close()
        return json.loads(fileData)
    else:
        return None


def write_file(text, filePath):
    writeFile = open(filePath, "w")
    writeFile.write(text)
    writeFile.close()


def write_json_list_file(listData, filePath):
    os.makedirs("data", exist_ok=True)
    jsonText = json.dumps([ob.__dict__ for ob in listData],
                          indent=4, default=datetime_to_string)
    write_file(jsonText, filePath)


def datetime_to_string(date_time):
    return date_time.strftime("%Y-%m-%dT%H:%M")


def string_to_datetime(string):
    return datetime.strptime(string, "%Y-%m-%dT%H:%M")

def html_to_markdown(html):
    return html2text.html2text(html)

def remove_html(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)


def get_dow_name(dayOfWeek):
    days = {
        0: "maandag",
        1: "dinsdag",
        2: "woensdag",
        3: "donderdag",
        4: "vrijdag",
        5: "zaterdag",
        6: "zondag",
    }
    return days.get(dayOfWeek)


def get_grade_updates():
    print("Getting grades..")
    grades_header = {"Authorization": "Bearer " +
                     access_token,
                     "Accept": "application/json"}
    grades_request = requests.get(
        endpoint + "/rest/v1/resultaten", headers=access_header)

    grades_json = json.loads(grades_request.text)
    # Currently the response is an 403
    # Something is wrong with the API idk
    print("Dumping the JSON grades output..")
    write_file(json.dumps(grades_json, indent=4),
               "data/somtoday_grades_output.json")

class HomeworkItem:
    def __init__(self, id, date_time, subject, abbreviation, homework_type, topic, description):
        self.id = id
        self.date_time = date_time
        self.subject = subject
        self.abbreviation = abbreviation
        self.type = homework_type
        self.topic = topic
        self.description = description

    def __eq__(self, other):
        return (self.id == other.id)

class ChangeType(Enum):
    NEW = 1
    DELETED = 2

class Update:
    def __init__(self, change_type, ref):
        self.type = change_type
        self.ref = ref


def get_homework_items(json_data):
    homework_items = []
    for item in json_data["items"]:
        homework_id = item["links"][0]["id"]
        if "datumTijd" in item:
            date_time_string = item["datumTijd"].split(".")[0]
            date_time = datetime.strptime(
                date_time_string, "%Y-%m-%dT%H:%M:%S")
        else:
            date_time = "Week"

        if "lesgroep" in item:
            subject = item["lesgroep"]["vak"]["naam"]
            abbreviation = item["lesgroep"]["vak"]["afkorting"]
        else:
            subject = item["studiewijzer"]["naam"]
            abbreviation = "Onbekend"

        homework_type = item["studiewijzerItem"]["huiswerkType"]
        topic = item["studiewijzerItem"]["onderwerp"]
        description = item["studiewijzerItem"]["omschrijving"]

        homework_items.append(HomeworkItem(homework_id, date_time,
                                           subject, abbreviation, homework_type, topic, description))
    return homework_items


def detect_homework_updates(old_items, new_items, date):
    found_changes = False
    updates = []

    # Check for new homework
    for item in new_items:
        if item not in old_items:
            found_changes = True
            updates.append(Update(ChangeType.NEW, item))

    # Check for deleted homework
    for item in old_items:
        if item.date_time.date() >= date:  # Only after specified date
            if item not in new_items:
                found_changes = True
                updates.append(Update(ChangeType.DELETED, item))
    return found_changes, updates

def create_homework_fields(homework_item):
    fields = {}
    fields["Datum"] = homework_item.date_time.strftime("%d-%m-%Y")
    fields["Tijd"] = homework_item.date_time.strftime("%H:%M")
    subject_short = homework_item.abbreviation.lower()
    if subject_short in subject_dict:
        fields["Vak"] = subject_dict[subject_short];
    else:
        fields["Vak"] = homework_item.subject

    fields["Type"] = homework_item.type.lower().capitalize()

    return fields

def homework_subjects(homework_list):
    all_subjects = []
    for item in homework_list:
        all_subjects.append(item.abbreviation.lower())
    short_subjects = list(dict.fromkeys(all_subjects))
    subject_names = []
    for short_subject in short_subjects:
        if short_subject in subject_dict:
            subject_names.append(subject_dict[short_subject])
        else:
            subject_names.append(short_subject.upper())
    subject_names = sorted(subject_names)
    return ', '.join(subject_names)

def notify_updates(updates):
    new_items = []
    deleted_items = []

    for update in updates:
        if update.type == ChangeType.NEW:
            new_items.append(update.ref)
        elif update.type == ChangeType.DELETED:
            deleted_items.append(update.ref)
    
    cards = []

    PREFIX = "**Van de vakken:** "
    SUFFIX = "\n\n_Zie https://somtoday.nl/ voor meer info_"

    if len(new_items) <= 3:
        for item in new_items:
            cards.append(notifier.NotificationCard("**Nieuw:** __{}__".format(item.topic), html_to_markdown(item.description), create_homework_fields(item)))
    else:
        cards.append(notifier.NotificationCard("{}x niew huiswerk!".format(len(new_items)), PREFIX + homework_subjects(new_items) + SUFFIX, None))
    
    if len(deleted_items) <= 3:
        for item in deleted_items:
            cards.append(notifier.NotificationCard("**Verwijderd:** __{}__".format(item.topic), html_to_markdown(item.description), create_homework_fields(item)))
    else:
        cards.append(notifier.NotificationCard("{}x verwijderd huiswerk!".format(len(deleted_items)), PREFIX + homework_subjects(new_items) + SUFFIX, None))

    notifier.notify(notifier.Notification("Er zijn veranderingen aan het huiswerk!", cards), "Somtoday")

def get_homework_updates():
    today = datetime.now().date()
    today_string = today.strftime("%Y-%m-%d")

    appt_hw_data = requests.get(
        endpoint + "/rest/v1/studiewijzeritemafspraaktoekenningen?begintNaOfOp=" + today_string, headers=access_header).text
    appt_hw_items = get_homework_items(json.loads(appt_hw_data))
    daily_hw_data = requests.get(
        endpoint + "/rest/v1/studiewijzeritemdagtoekenningen?begintNaOfOp=" + today_string, headers=access_header).text
    daily_hw_items = get_homework_items(json.loads(daily_hw_data))
    # weekly_hw_data = requests.get(
    #     endpoint + "/rest/v1/studiewijzeritemweektoekenningen?begintNaOfOp=" + today_string, headers=access_header).text
    # weekly_hw_items = get_homework_items(json.loads(weekly_hw_data))

    # print("Dumping homework json...")
    # write_json_list_file(appt_hw_items, "data/somtoday_appointment_homework.json")
    # write_json_list_file(daily_hw_items, "data/somtoday_daily_homework.json")
    # write_json_list_file(weekly_hw_items, "data/somtoday_weekly_homework.json")

    print("Done! Detecting changes (DISABLED)")

    homework_items = []
    homework_items.extend(appt_hw_items)
    homework_items.extend(daily_hw_items)
    homework_items.sort(key=lambda x: x.date_time)

    # Detect changes
    old_homework_json = read_json_file("data/somtoday_homework.json")
    if old_homework_json != None:
        old_homework_items = []
        for item in old_homework_json:
            old_homework_items.append(HomeworkItem(item["id"], string_to_datetime(
                item["date_time"]), item["subject"], item["abbreviation"], item["type"], item["topic"], item["description"]))

        found_changes, updates = detect_homework_updates(
            old_homework_items, homework_items, today)

        if found_changes:
            print("Updated, found {} homework updates! Sending notifications..".format(
                len(updates)))
            notify_updates(updates)
        else:
            print("Updated, no changes found.")

    write_json_list_file(homework_items, "data/somtoday_homework.json")


def update():
    authenticate()

    get_grade_updates()
    get_homework_updates()


# The application loop
load_credentials()
get_school_uuid()
update()

# Schedule the updating
scheduler = BlockingScheduler()
scheduler.add_job(update, "interval", seconds=sync_interval)
print("Updating SOMToday every " +
      str(sync_interval) + " seconds..")
scheduler.start()
