import datetime
import time
import requests
import json
import os
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

FETCH_DAYS = 10 # Delete known days when decreasing the ammount
sync_delay = 30

with open('config/settings.json') as settings_file:
    settings_json = json.load(settings_file)
    sync_delay = int(settings_json["sync_delay"])

with open('config/subjects.json') as file:
    subject_list = json.loads(file.read())
with open('config/teachers.json') as file:
    teacher_list = json.loads(file.read())

organization = None
auth_code = None
endpoint = None
access_token = None
group_names = None
group_ids = None
expiration_time = None

def load_credentials():
    global organization
    global auth_code
    global endpoint
    global group_names
    with open('config/zermelo_credentials.json') as config_file:
        config_json = json.load(config_file)
        group_names = config_json["group_names"]
        organization = config_json["organization"]
        auth_code = config_json["auth_code"].replace(" ", "") # Remove the spaces from code (useful for copying)
    endpoint = "https://{}.zportal.nl/api/v3/".format(organization)

def appointment_to_fields(appointment):
    subject_short = ', '.join(appointment.subjects)
    if subject_short in subject_list:
        subject_name = subject_list[subject_short]
    else:
        subject_name = subject_short.upper()

    teacher_short = ', '.join(appointment.teachers)
    if teacher_short in teacher_list:
        teacher_name = teacher_list[teacher_short]
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
    
def apppointment_message(appointment, info):
    fields = appointment_to_fields(appointment)
    notifier.notify(("__{}__ " + info).format(fields["Vak"]), appointment_to_fields(appointment), "Zermelo")

def new_appointment(appointment):
    apppointment_message(appointment, "is toegevoegd")

def removed_appointment(appointment):
    apppointment_message(appointment, "valt uit!")

def combine_field_changes(before, after):
    combined = {}
    for key, value in after.items():
        original = before[key]
        if str(value) != str(original):
            combined[key] = "{} 🡆 {}".format(original, value);
        else:
            combined[key] = value;
    return combined;

def changed_appointment(old, new):
    old_fields = appointment_to_fields(old)
    new_fields = appointment_to_fields(new)
    fields = combine_field_changes(old_fields, new_fields)
    notifier.notify(("__{}__ is aangepast").format(fields["Vak"]), fields, "Zermelo")

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
        
        os.makedirs("data", exist_ok=True)
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
        error_title = str(token_response.status_code) + " " + token_response.reason + " - authentication failed"
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

    groups_response = requests.get(endpoint + "groupindepartments?access_token=" + access_token)

    if not groups_response.ok:
        notifier.notify_error("{} {} - failed to get groups".format(groups_response.status_code, groups_response.reason), 
        "Response: '{}'".format(groups_response.text))
        return

    groups_json = groups_response.json()['response']['data']

    os.makedirs("data", exist_ok=True)
    with open("data/zermelo_groups_dump.json", "w+") as f:
        f.write(json.dumps(groups_json, default=datetime_to_string))

    group_ids = []
    found_group_names = []
    for item in groups_json:
        for group_name in group_names:
            if group_name in found_group_names: # Only use the first group id found
                continue
            if item["name"] == group_name and item["isMentorGroup"] and item["isMainGroup"]:
                group_ids.append(item["id"])
                found_group_names.append(group_name)

    if len(group_ids) > 0:
        print("Group IDs: {}".format(group_ids))
    else:
        notifier.notify_error("Couldn't find the group IS(s)!", "Groups names: {}".format(group_names))

class Appointment:
    def __init__(self, id, start: datetime.datetime, end: datetime.datetime, start_time_slot, end_time_slot, teachers, subjects, locations):
        self.id = id
        self.start = start
        self.end = end
        self.start_time_slot = start_time_slot # Int or None
        self.end_time_slot = end_time_slot # Int or None
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
    update_count = 0
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
                update_count += 1
                changed_appointment(old_appt, new_appt)
        else:
            if new_appt.start.date() in known_dates: # Only notify if this was on a known date
                found_updates = True
                update_count += 1
                new_appointment(new_appt)
    
    # Check if the appointment still exists or if it got removed
    for old_appt in old_appts:
        found_appt = False
        if not old_appt in new_appts:
            if old_appt.start.date() in known_dates:  # Only notify if this was on a known date
                found_updates = True
                update_count += 1
                removed_appointment(old_appt)
    return found_updates, update_count

def get_schedule_updates():
    today = datetime.date.today()
    start_date = today
    end_date = today + timedelta(days=FETCH_DAYS)
    timestamp_start = str(int(time.mktime(start_date.timetuple())))
    timestamp_end = str(int(time.mktime(end_date.timetuple())))
    
    print("Fetching appointments from {} to {}..".format(date_to_string(today), date_to_string(end_date)))
    appointments = []

    for id in group_ids:
        new_appointments = get_appointments(id, timestamp_start, timestamp_end);
        if not new_appointments:
            print("\nSomething went wrong while fetching the appointments!")
            return;
        appointments.extend(new_appointments)
    
    appointments = sorted(appointments)
    
    print("Got {} appointments!".format(len(appointments)));

    # Compare and detect changes
    print("Detecting changes..")
    known_dates = []
    if os.path.exists("data/zermelo_appointments.json"):
        found_changes = False
        os.makedirs("data", exist_ok=True)
        
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

        found_changes, update_count = detect_appointment_updates(previous_appointments, appointments, known_dates)
        
        if not found_changes:
            print("Updated, no changes found.")
        else:
            print("Updated, found {} schedule changes.".format(update_count))
    
    # Save new json
    os.makedirs("data", exist_ok=True)
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
scheduler.add_job(update, "interval", seconds=sync_delay)
print("Updating schedule changes every " +
      str(sync_delay) + " seconds..")
scheduler.start()