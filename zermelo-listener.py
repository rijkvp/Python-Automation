import datetime
import time
import requests
import json
import os
from enum import Enum
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import timedelta
import operator
import notifier

# The dutch weekday abbreviations
WEEKDAY_ABBREVIATIONS = {
    0: "Ma",
    1: "Di",
    2: "Wo",
    3: "Do",
    4: "Vr",
    5: "Za",
    6: "Zo"
}

# The amount of days to look into the future
# WARNING: Delete the known days file when decreasing the ammount! Otherwise the program thinks the appointments are cancelled
FETCH_DAYS = 10


sync_interval = 30

# Make sure the folders exist
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

if os.path.exists('config/teachers.json'):
    with open('config/teachers.json') as file:
        teacher_dict = json.loads(file.read())
else:
    teacher_dict = None
    
organization = None
auth_code = None
endpoint = None
access_token = None
group_names = None
group_ids = None
expiration_time = None
website = None


def load_credentials():
    global organization
    global auth_code
    global endpoint
    global group_names
    global group_ids
    global website
    with open('config/zermelo_credentials.json') as config_file:
        config_json = json.load(config_file)
        group_names = config_json["group_names"]
        if "group_ids" in config_json:
            group_ids = config_json["group_ids"]
        organization = config_json["organization"]
        # Remove the spaces from code (useful for copying)
        auth_code = config_json["auth_code"].replace(" ", "")
    endpoint = "https://{}.zportal.nl/api/v3/".format(organization)
    website = "https://{}.zportal.nl".format(organization)


def appointment_to_fields(appointment):
    subject_short = ', '.join(appointment.subjects)
    if subject_short in subject_dict:
        subject_name = subject_dict[subject_short]
    else:
        subject_name = subject_short.upper()

    teacher_short = ', '.join(appointment.teachers)
    if teacher_short in teacher_dict:
        teacher_name = teacher_dict[teacher_short]
    else:
        teacher_name = teacher_short.upper()
    location = ', '.join(appointment.locations)
    weekday = WEEKDAY_ABBREVIATIONS[appointment.start.weekday()]
    return {
        "Vak": subject_name,
        "Docent": teacher_name,
        "Lokaal": location,
        "Lesuur": appointment.start_time_slot,
        "Datum": weekday + " " + appointment.start.strftime("%d-%m"),
        "Tijd": appointment.start.strftime("%H:%M") + " - " + appointment.end.strftime("%H:%M")
    }


def new_appointment_card(appointment):
    fields = appointment_to_fields(appointment)
    return notifier.NotificationCard(("__{}__ is toegevoegd").format(fields["Vak"]), None, fields)


def cancelled_appointment_card(appointment):
    fields = appointment_to_fields(appointment)
    return notifier.NotificationCard(("__{}__ valt uit!").format(fields["Vak"]), None, fields)


def combine_field_changes(before, after):
    combined = {}
    for key, value in after.items():
        original = before[key]
        if str(value) != str(original):
            combined[key] = "{} 🡆 {}".format(original, value)
        else:
            combined[key] = value
    return combined


def changed_appointment_card(old, new):
    old_fields = appointment_to_fields(old)
    new_fields = appointment_to_fields(new)
    fields = combine_field_changes(old_fields, new_fields)
    return notifier.NotificationCard(("__{}__ is aangepast").format(fields["Vak"]), None, fields)


def format_subject_list(subject_list):
    all_subjects = []
    for subjects in subject_list:
        for subject in subjects:
            all_subjects.append(subject.lower())
    short_subjects = list(dict.fromkeys(all_subjects))
    subject_names = []
    for short_subject in short_subjects:
        if short_subject in subject_dict:
            subject_names.append(subject_dict[short_subject])
        else:
            subject_names.append(short_subject.upper())
    subject_names = sorted(subject_names)
    return ', '.join(subject_names)


def authenticate():
    global access_token
    global expiration_time

    if os.path.isfile('data/zermelo_access_token.json'):
        with open("data/zermelo_access_token.json") as file:
            json_data = json.loads(file.read())
            access_token = json_data["access_token"]
            expiration_time = string_to_datetime(json_data["expiration_time"])
            # Testing: Don't check
            # if expiration_time < datetime.datetime.now():
            #     print("Access token is expired - getting new..")
            # else:
            #     print("Found valid access token.")
            #     return
            print("Skipped checking token expiration!")
            return

    data = {"grant_type": "aucthorization_code", "code": auth_code}
    header = {"Accept": "application/json"}
    token_response = requests.post(
        endpoint + "oauth/token", data=data, headers=header)
    if token_response.ok:
        token_json = json.loads(token_response.text)
        access_token = token_json["access_token"]

        print("Got access token: {}".format(access_token))
        expiration_delay = token_json["expires_in"]
        expiration_time = datetime.datetime.now() + timedelta(seconds=expiration_delay)
        print("Expires on: " + datetime_to_string(expiration_time))

        
        with open("data/zermelo_access_token.json", "w") as file:
            access_token_json = {
                "access_token": access_token,
                "expiration_time": datetime_to_string(expiration_time)
            }
            file.write(json.dumps(access_token_json))
    elif token_response.status_code == 400:
        access_token = None
        expiration_time = None
        error_title = "Failed to authenticate!"
        error_msg = "Invalid credentials, make sure your auth code & organization are correct and valid."
        notifier.notify_error(error_title, error_msg)
    else:
        access_token = None
        expiration_time = None
        error_title = str(token_response.status_code) + " " + \
            token_response.reason + " - authentication failed"
        error_msg = "Response: '" + token_response.text + "'\nMake sure the credentials are valid in zermelo_credentials.json:\nSchool code: {0}, Auth code: {1}".format(
            organization, auth_code)

        notifier.notify_error(error_title, error_msg)


def convert_timestamp(timestamp):
    return datetime.datetime.fromtimestamp(timestamp)


def datetime_to_string(date_time):
    return date_time.strftime("%Y-%m-%dT%H:%M")


def date_to_string(date):
    return date.strftime("%Y-%m-%d")


def string_to_datetime(string):
    return datetime.datetime.strptime(string, "%Y-%m-%dT%H:%M")


def string_to_date(string):
    return datetime.datetime.strptime(string, "%Y-%m-%d").date()


def get_group_ids():
    global group_ids

    groups_response = requests.get(
        endpoint + "groupindepartments?access_token=" + access_token)

    if not groups_response.ok:
        notifier.notify_error("{} {} - failed to get groups".format(groups_response.status_code, groups_response.reason),
                              "Response: '{}'".format(groups_response.text))
        return

    groups_json = groups_response.json()['response']['data']

    with open("data/zermelo_groups_dump.json", "w+") as f:
        f.write(json.dumps(groups_json, default=datetime_to_string))

    print("No group id's specified. Searching for group id's with group names: {}".format(
        group_names))
    group_ids = []
    for item in groups_json:
        for group_name in group_names:
            if item["name"] == group_name and item["isMentorGroup"] and item["isMainGroup"]:
                group_ids.append(item["id"])

    if len(group_ids) > 0:
        print("Found {} group IDs: {}".format(len(group_ids), group_ids))
    else:
        notifier.notify_error("Couldn't find the group ID(s)!",
                              "The groups names are: {}".format(group_names))


class Appointment:
    def __init__(self, id, start: datetime.datetime, end: datetime.datetime, start_time_slot, end_time_slot, teachers, subjects, locations):
        self.id = id
        self.start = start
        self.end = end
        self.start_time_slot = start_time_slot  # Int or None
        self.end_time_slot = end_time_slot  # Int or None
        self.teachers = teachers
        self.subjects = subjects
        self.locations = locations

    def __eq__(self, obj):
        return self.id == obj.id

    def has_changed(self, obj):
        return not (self.start == obj.start and self.end == obj.end and self.teachers == obj.teachers and self.subjects == obj.subjects and self.locations == obj.locations)

    def __lt__(self, other):
        return self.start < other.start

    def as_dict(self):
        return {
            "id": str(self.id),
            "start": datetime_to_string(self.start),
            "end": datetime_to_string(self.end),
            "start_time_slot": str(self.start_time_slot),
            "end_time_slot": str(self.end_time_slot),
            "teachers": list(self.teachers),
            "subjects": list(self.subjects),
            "locations": list(self.locations),
        }


class ChangeType(Enum):
    NEW = 1
    CANCELLED = 2
    CHANGED = 3


class AppointmentUpdate:
    def __init__(self, old_appointment, new_appointment, type):
        self.old_appointment = old_appointment
        self.new_appointment = new_appointment
        self.type = type


def get_appointments(group_id, timestamp_start, timestamp_end):
    appointments = []
    appointment_response = requests.get(endpoint + "appointments?access_token=" + access_token +
                                        "&start=" + timestamp_start + "&end="+timestamp_end+"&valid=true" + "&containsStudentsFromGroupInDepartment=" + str(group_id))

    if not appointment_response.ok:
        notifier.notify_error("{} {} - failed to get appointments!".format(appointment_response.status_code, appointment_response.reason),
                              "Group ID: {}, Response: '{}'".format(group_id, appointment_response.text))
        return

    appointment_data = appointment_response.json()['response']['data']

    for appointment in appointment_data:
        if appointment["cancelled"] == False:
            appointments.append(Appointment(appointment["appointmentInstance"], convert_timestamp(appointment['start']), convert_timestamp(
                appointment['end']), appointment['startTimeSlot'], appointment['endTimeSlot'], set(appointment['teachers']), set(appointment['subjects']), set(appointment['locations'])))

    return appointments


def detect_appointment_updates(old_appts, new_appts, known_dates):
    found_updates = False
    updates = []
    for new_appt in new_appts:
        found_appt = False
        old_appt = None
        for appt in old_appts:
            if appt == new_appt:
                found_appt = True
                old_appt = appt
                break

        if found_appt:
            if new_appt.has_changed(old_appt):
                found_updates = True
                updates.append(AppointmentUpdate(
                    old_appt, new_appt, ChangeType.CHANGED))
        else:
            if new_appt.start.date() in known_dates:  # Only notify if this was on a known date
                found_updates = True
                updates.append(AppointmentUpdate(
                    None, new_appt, ChangeType.NEW))

    # Check if the appointment still exists or if it got removed
    for old_appt in old_appts:
        found_appt = False
        if not old_appt in new_appts:
            if old_appt.start.date() in known_dates:  # Only notify if this was on a known date
                found_updates = True
                updates.append(AppointmentUpdate(
                    old_appt, None, ChangeType.CANCELLED))

    return found_updates, updates


def notify_updates(updates):
    new_updates = []
    cancelled_updates = []
    changed_updates = []
    for update in updates:
        if update.type == ChangeType.NEW:
            new_updates.append(update)
        elif update.type == ChangeType.CANCELLED:
            cancelled_updates.append(update)
        elif update.type == ChangeType.CHANGED:
            changed_updates.append(update)

    cards = []
    if len(cancelled_updates) <= 3:
        for update in cancelled_updates:
            cards.append(cancelled_appointment_card(update.old_appointment))
    else:
        cards.append(notifier.NotificationCard("Er zijn {} vervallen lessen:".format(len(cancelled_updates)),
                                               "**Van de vakken:** " + format_subject_list([u.old_appointment.subjects for u in cancelled_updates]) + "\n\n_Zie " + website + " voor meer info_", None))

    if len(new_updates) <= 3:
        for update in new_updates:
            cards.append(new_appointment_card(update.new_appointment))
    else:
        cards.append(notifier.NotificationCard("Er zijn {} toegevoegde lessen:".format(len(
            new_updates)), "**Van de vakken:** " + format_subject_list([u.new_appointment.subjects for u in new_updates]) + "\n\n_Zie " + website + " voor meer info_", None))

    if len(changed_updates) <= 3:
        for update in changed_updates:
            cards.append(changed_appointment_card(
                update.old_appointment, update.new_appointment))
    else:
        cards.append(notifier.NotificationCard("Er zijn {} lessen zijn aangepast:".format(len(
            changed_updates)), "**Van de vakken:** " + format_subject_list([u.new_appointment.subjects for u in changed_updates]) + "\n\n_Zie " + website + " voor meer info_", None))

    update_notification = notifier.Notification(
        "Het zermelo rooster is gewijzigd:", cards)
    notifier.notify(update_notification, "Zermelo")


def get_schedule_updates():
    today = datetime.date.today()
    start_date = today
    end_date = today + timedelta(days=FETCH_DAYS)
    timestamp_start = str(int(time.mktime(start_date.timetuple())))
    timestamp_end = str(int(time.mktime(end_date.timetuple())))

    print("Fetching appointments from {} to {}..".format(
        date_to_string(today), date_to_string(end_date)))
    appointments = []

    multiple_groups = len(group_ids) > 1

    for id in group_ids:
        new_appointments = get_appointments(id, timestamp_start, timestamp_end)
        if new_appointments == None:
            print(
                "Didn't get any data! Something went wrong while fetching the appointments!")
            return
        elif len(new_appointments) == 0:
            print(
                "Didn't find any appointments for the next {} days..".format(FETCH_DAYS))
            return

        if multiple_groups:
            for new_item in new_appointments:
                if not new_item in appointments:
                    appointments.append(new_item)
        else:
            appointments.extend(new_appointments)

    appointments = sorted(appointments)

    print("Got {} appointments!".format(len(appointments)))

    # Compare and detect changes
    print("Detecting changes..")
    known_dates = []
    if os.path.exists("data/zermelo_appointments.json"):
        found_changes = False

        if os.path.exists("data/zermelo_known_dates.json"):
            with open("data/zermelo_known_dates.json", "r") as f:
                known_dates_json = json.loads(f.read())
            for date_json in known_dates_json:
                date = string_to_date(date_json)
                if date >= today:
                    known_dates.append(date)

        previous_appointments = []
        with open("data/zermelo_appointments.json", "r") as f:
            previous_json = json.loads(f.read())

        for appointment in previous_json:
            previous_appointments.append(Appointment(int(appointment["id"]), string_to_datetime(appointment['start']), string_to_datetime(
                appointment['end']), appointment['start_time_slot'], appointment['end_time_slot'], set(appointment['teachers']), set(appointment['subjects']), set(appointment['locations'])))

        found_changes, updates = detect_appointment_updates(
            previous_appointments, appointments, known_dates)

        if found_changes:
            print("Updated, found {} schedule changes! Sending notifications..".format(
                len(updates)))
            notify_updates(updates)
        else:
            print("Updated, no changes found.")

    # Save new json
    appointment_json = json.dumps(
        [a.as_dict() for a in appointments])
    with open("data/zermelo_appointments.json", "w+") as f:
        f.write(appointment_json)

    for appt in appointments:
        appt_date = appt.start.date()
        if appt_date not in known_dates:
            known_dates.append(appt_date)
            print("New known date: " + date_to_string(appt_date))

    dates_json = json.dumps([date_to_string(d) for d in known_dates])
    with open("data/zermelo_known_dates.json", "w+") as f:
        f.write(dates_json)


def update():
    # Load user config - credentials
    load_credentials()

    # First, make sure the portal is online
    portal_status = requests.get(endpoint + "status/status_message")
    if not portal_status.ok:
        notifier.notify_error("Portal is offline",
                              "{} - {}\n{}\nEndpoint: {}".format(portal_status.status_code, portal_status.reason, portal_status.text, endpoint))
        return

    # Then, receive the acces token if not already done
    if access_token is None:
        authenticate()

    # Finally, get the schedule updates
    if access_token is not None:
        if group_ids is None:
            get_group_ids()
        if group_ids is not None:
            get_schedule_updates()


update()
scheduler = BlockingScheduler()
scheduler.add_job(update, "interval", seconds=sync_interval)
print("Updating schedule changes every " +
      str(sync_interval) + " seconds..")
scheduler.start()
