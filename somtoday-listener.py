from os.path import join
from apscheduler.schedulers.blocking import BlockingScheduler
import requests
import json
from datetime import datetime
import os
from enum import Enum
import notifier
import html2text

BASE_URL = "https://production.somtoday.nl"

sync_interval = 30

# Make sure folders exist
os.makedirs("config", exist_ok=True)
os.makedirs("data", exist_ok=True)

with open('config/settings.json') as settings_file:
    settings_json = json.load(settings_file)
    sync_interval = int(settings_json["sync_interval"])

if os.path.exists('config/subjects.json'):
    with open('config/subjects.json') as file:
        subject_dict = json.loads(file.read())
else:
    subject_dict = None

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
student_id = None


def authenticate():
    global access_token
    global endpoint
    global access_header
    global refresh_token
    is_authenticated = access_token is not None
    data = {"grant_type": "password",
            "username": school_uuid + "\\" + username,
            "password": password,
            "scope": "openid",
            "client_id": "D50E0C06-32D1-4B41-A137-A9A850C892C2"}

    access_headers = {"Accept": "application/json"}
    token_request = None
    if access_token == None:
        token_request = requests.post(
            BASE_URL + "/oauth2/token", data=data, headers=access_headers)
        if token_request.status_code == 500:
            print("Unable to authenticate! Are the servers down?! Response: 500")
        elif token_request.status_code == 200:
            print("Successfully logged in!")
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
        None
        # print("Refreshing the token..")
        # data = {"grant_type": "refresh_token",
        #         "refresh_token": refresh_token}
        # refresh_request = requests.post(
        #     BASE_URL + "/oauth2/token", data=data, headers=access_headers)
        # token_json = json.loads(refresh_request.text)

        # access_token = token_json["access_token"]
        # refresh_token = token_json["refresh_token"]
        # endpoint = token_json["somtoday_api_url"]
        # access_header = {"Authorization": "Bearer " +
        #                  access_token, "Accept": "application/json"}
        # is_authenticated = True
    if is_authenticated == False and token_request is not None:
        print("\nFailed to authenticate! Are your credentials right?\n\n{} - {}\n{}".format(
            token_request.status_code, token_request.reason, token_request.text))
        exit()


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
    jsonText = json.dumps([ob.__dict__ for ob in listData],
                          indent=4, default=datetime_to_string)
    write_file(jsonText, filePath)


def datetime_to_string(date_time):
    return date_time.strftime("%Y-%m-%dT%H:%M")


def string_to_datetime(string):
    return datetime.strptime(string, "%Y-%m-%dT%H:%M")


def html_to_markdown(html):
    return html2text.html2text(html)


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


def get_subject_name(subject):
    if subject.lower() in subject_dict:
        return subject_dict[subject.lower()]
    else:
        return subject


def get_student_id():
    students_request = requests.get(
        endpoint + "/rest/v1/leerlingen", headers=access_header)
    students_json = json.loads(students_request.text)
    global student_id
    student_id = students_json["items"][0]["links"][0]["id"]


class ChangeType(Enum):
    NEW = 1
    DELETED = 2


class Update:
    def __init__(self, change_type, ref):
        self.type = change_type
        self.ref = ref


class Grade:
    def __init__(self, id, grade, weight, description, subject):
        self.id = id
        self.grade = grade
        self.weight = weight
        self.description = description
        self.subject = subject

    def __eq__(self, other):
        return (self.id == other.id)


def get_grade_items():
    grades_header = {"Authorization": "Bearer " +
                     access_token, "Accept": "application/json",
                     # Range is probably not needed
                     # "range": "items=0-99"
                     }
    grades_url = endpoint + \
        "/rest/v1/resultaten/huidigVoorLeerling/" + str(student_id)
    grades_request = requests.get(grades_url, headers=grades_header)

    grades_json = json.loads(grades_request.text)
    write_file(json.dumps(grades_json, indent=4),
               "data/somtoday_grades_output.json")

    grade_items = []

    for grade_json in grades_json["items"]:
        if grade_json["type"] == "Toetskolom":
            if "weging" in grade_json:
                weight = grade_json["weging"]
            elif "examenWeging" in grade_json:
                weight = str(grade_json["examenWeging"]) + " SE"
            else:
                weight = None
            description = grade_json["omschrijving"] if "omschrijving" in grade_json else None
            grade_items.append(Grade(grade_json["links"][0]["id"], grade_json["resultaat"], weight,
                                     description, grade_json["vak"]["afkorting"]))

    print("Got {} valid grades with {} items in total..".format(
        len(grade_items), len(grades_json["items"])))
    return grade_items


def detect_grade_updates(old_items, new_items):
    found_changes = False
    updates = []

    for item in new_items:
        if item not in old_items:
            found_changes = True
            updates.append(Update(ChangeType.NEW, item))

    return found_changes, updates


def create_grade_fields(grade):
    fields = {}
    fields["Cijfer"] = grade.grade
    fields["Weging"] = grade.weight
    fields["Omschrijving"] = grade.description
    fields["Vak"] = get_subject_name(grade.subject)

    return fields


def format_grade_list(items, remove_emoji=False, short=False):
    grades_list = []
    for grade in items:
        if not short:
            subject_name = get_subject_name(grade.subject)
            if remove_emoji:
                subject_name = notifier.remove_discord_emoji(subject_name)
        else:
            subject_name = grade.subject.upper()
        if not short:
            seperator = "voor"
        else:
            seperator = "→"
        grades_list.append("{} {} {} ({}x)".format(
            grade.grade, seperator, subject_name, grade.weight))

    return grades_list


def notify_grade_updates(updates):
    new_items = []
    deleted_items = []

    for update in updates:
        if update.type == ChangeType.NEW:
            new_items.append(update.ref)
        elif update.type == ChangeType.DELETED:
            deleted_items.append(update.ref)

    cards = []

    PREFIX = "**Cijfers:** "
    SUFFIX = "\n\n_Zie https://somtoday.nl/ voor meer info_"

    if len(new_items) <= 10:
        for item in new_items:
            cards.append(notifier.NotificationCard("**__{}__** voor {}!".format(item.grade, get_subject_name(item.subject)),
                                                   html_to_markdown(item.description), create_grade_fields(item)))
    else:
        cards.append(notifier.NotificationCard("{} nieuwe cijfers!".format(
            len(new_items)), PREFIX + ", ".join(format_grade_list(new_items)) + SUFFIX, None))

    if len(new_items) == 1:
        new_grade = new_items[0]
        short_title = "{} gehaald voor {} ({}x)!".format(new_grade.grade, notifier.remove_discord_emoji(
            get_subject_name(new_grade.subject)), new_grade.weight)
        short_description = new_grade.description
    else:
        short_title = "{} nieuwe cijfers!".format(len(new_items))
        short = len(new_items) > 2
        short_description = ", ".join(
            format_grade_list(new_items, True, short)) + "."

    notifier.notify(notifier.Notification(
        "Er zijn nieuwe cijfers!", cards, short_title, short_description), "Somtoday-Grades")


def get_grade_updates():
    grades = get_grade_items()

    # Detect changes
    old_grade_json = read_json_file("data/somtoday_grades.json")
    if old_grade_json != None:
        old_grades = []
        for grade in old_grade_json:
            old_grades.append(Grade(
                grade["id"], grade["grade"], grade["weight"], grade["description"], grade["subject"]))

        found_changes, updates = detect_grade_updates(old_grades, grades)

        if found_changes:
            print("Updated, found {} grade updates! Sending notifications..".format(
                len(updates)))
            notify_grade_updates(updates)
        else:
            print("Updated grades, no changes found.")

    write_json_list_file(grades, "data/somtoday_grades.json")


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


def convert_homework_items(json_data):
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
    fields["Vak"] = get_subject_name(homework_item.subject)
    fields["Type"] = homework_item.type.lower().capitalize()

    return fields


def homework_subjects(homework_list):
    all_subjects = []
    for item in homework_list:
        all_subjects.append(item.abbreviation.lower())
    subject_abbrevs = list(dict.fromkeys(all_subjects))
    subject_names = []
    for abbrev in subject_abbrevs:
        subject_names.append(get_subject_name(abbrev))
    subject_names = sorted(subject_names)
    return subject_names


def get_update_refs(updates):
    return [u.ref for u in updates]


def notify_homework_updates(updates):
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

    if len(new_items) <= 4:
        for item in new_items:
            cards.append(notifier.NotificationCard("**Nieuw:** __{}__".format(item.topic),
                                                   html_to_markdown(item.description), create_homework_fields(item)))
    else:
        cards.append(notifier.NotificationCard("{}x nieuw huiswerk!".format(
            len(new_items)), PREFIX + ', '.join(homework_subjects(new_items)) + SUFFIX, None))

    if len(deleted_items) <= 4:
        for item in deleted_items:
            cards.append(notifier.NotificationCard("**Verwijderd:** __{}__".format(
                item.topic), html_to_markdown(item.description), create_homework_fields(item)))
    else:
        cards.append(notifier.NotificationCard("{}x verwijderd huiswerk!".format(
            len(deleted_items)), PREFIX + ', '.join(homework_subjects(new_items)) + SUFFIX, None))

    title_parts = []
    if len(new_items) > 0:
        title_parts.append("{}x nieuw".format(len(new_items)))
    if len(deleted_items) > 0:
        title_parts.append("{}x verwijderd".format(len(deleted_items)))

    short_title = "Huiswerk: " + ", ".join(title_parts)
    subject_names = [notifier.remove_discord_emoji(
        s) for s in homework_subjects(get_update_refs(updates))]
    short_description = "Van: " + ", ".join(subject_names) + "."

    notifier.notify(notifier.Notification(
        "Er zijn veranderingen aan het huiswerk!", cards, short_title, short_description), "Somtoday-Homework")


def get_homework_updates():
    today = datetime.now().date()
    today_string = today.strftime("%Y-%m-%d")

    appt_hw_data = requests.get(
        endpoint + "/rest/v1/studiewijzeritemafspraaktoekenningen?begintNaOfOp=" + today_string, headers=access_header).text
    appt_hw_items = convert_homework_items(json.loads(appt_hw_data))
    daily_hw_data = requests.get(
        endpoint + "/rest/v1/studiewijzeritemdagtoekenningen?begintNaOfOp=" + today_string, headers=access_header).text
    daily_hw_items = convert_homework_items(json.loads(daily_hw_data))

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
            notify_homework_updates(updates)
        else:
            print("Updated homework, no changes found.")

    write_json_list_file(homework_items, "data/somtoday_homework.json")


def update():
    authenticate()

    get_student_id()
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
