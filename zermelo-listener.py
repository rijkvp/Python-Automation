import datetime
import time
import requests
import json
import os
from apscheduler.schedulers.blocking import BlockingScheduler
from plyer import notification
from datetime import timedelta
from deepdiff import DeepDiff

sync_delay = 30

with open('config/settings.json') as settings_file:
    settings_json = json.load(settings_file)
    sync_delay = int(settings_json["sync_delay"])


organization = None
auth_code = None
endpoint = None
access_token = None
user_name = None


def load_credentials():
    global organization
    global auth_code
    global endpoint
    global user_name
    with open('config/zermelo_credentials.json') as config_file:
        config_json = json.load(config_file)
        user_name = config_json["user_name"]
        organization = config_json["organization"]
        auth_code = config_json["auth_code"]
    endpoint = "https://{}.zportal.nl/api/v3/".format(organization)


def send_notification(title, body):
    notification.notify(title, body)


def get_access_token():
    global access_token

    if os.path.isfile('data/zermelo_access_token.json'):
        with open("data/zermelo_access_token.json") as file:
            json_data = json.loads(file.read()) 
            access_token = json_data["access_token"] # TODO: Check if the access token hasn't been expired
            return

    data = {"grant_type": "authorization_code", "code": auth_code}
    header = {"Accept": "application/json"}
    token_response = requests.post(
        endpoint + "oauth/token", data=data, headers=header)
    if token_response.ok:
        print("Token: " + str(token_response.status_code) + " - " + token_response.reason +
              "\nText: " + token_response.text)
        token_json = json.loads(token_response.text)
        access_token = token_json["access_token"]
        print("Acces token: {}".format(access_token))
        
        os.makedirs("data", exist_ok=True)
        with open("data/zermelo_access_token.json", "w") as file:
            access_token_json = {
                "access_token": access_token,
                "expires": "todo"
            }
            file.write(json.dumps(access_token_json))
    else:
        error_msg = "Couldn't authenticate the access token! Make sure the credentials are right!\nSchool code: {0}\nAuth code (without spaces!): {1}".format(
            organization, auth_code)

        print(error_msg)
        send_notification("Couldn't Authenticate!", error_msg)


def get_schedule_updates():
    today = datetime.date.today()
    start_date = today
    end_date = today + timedelta(days=14)
    timestamp_start = str(int(time.mktime(start_date.timetuple())))
    timestamp_end = str(int(time.mktime(end_date.timetuple())))
    json_response = requests.get(endpoint + "appointments?user=" + user_name + "&access_token=" + access_token +
                                 "&start=" + timestamp_start + "&end="+timestamp_end+"&valid=true").json()
    appointment_data = json_response['response']['data']

    def start_field(appointment):
        return int()

    appointment_data.sort(key=start_field)

    def convert_timestamp(timestamp):
        return datetime.datetime.fromtimestamp(timestamp)

    def datetime_to_string(date_time):
        return date_time.strftime("%Y-%m-%dT%H:%M")

    class Appointment:
        def __init__(self, start, end, start_time_slot, teachers, subjects, locations):
            self.start = start
            self.end = end
            self.start_time_slot = start_time_slot
            self.teachers = teachers
            self.subjects = subjects
            self.locations = locations

    appointments = []

    for appointment in appointment_data:
        appointments.append(Appointment(convert_timestamp(appointment['start']), convert_timestamp(
            appointment['end']), appointment['startTimeSlot'], appointment['teachers'], appointment['subjects'], appointment['locations']))

    appointment_json = json.dumps(
        [ob.__dict__ for ob in appointments], default=datetime_to_string)

    # Load previous data
    with open("data/zermelo_appointments.json", "r") as f:
        previous_json = f.read()

    # DeefDiff library calculates difference bewteen previous & new json
    difference = DeepDiff(json.loads(appointment_json), json.loads(previous_json), view='tree')
    print("Difference:\n" + str(difference))
    if "values_changed" in difference:
        for change in difference["values_changed"]:
            print("1: " + change.t1 + " 2: " + change.t2);
            print(change);
            print(change.up);

    # Save new json
    os.makedirs("data", exist_ok=True)
    with open("data/zermelo_appointments.json", "w") as f:
        f.write(json.dumps([ob.__dict__ for ob in appointments], default=datetime_to_string))


def update():
    # Load user config - credentials
    load_credentials()

    # First, make sure the portal is online
    portal_status = requests.get(endpoint + "status/status_message")
    if not portal_status.ok:
        print("Couldn't connect to the portal. Endpoint: {0}, Status: {1}, Message: {2}".format(
            endpoint, portal_status.status_code, portal_status.text))
        return

    # Then, receive the acces token if not already done
    if access_token is None:
        get_access_token()

    # Finally, get the schedule updates
    if access_token is not None:
        get_schedule_updates()


scheduler = BlockingScheduler()
scheduler.add_job(update, "interval", seconds=sync_delay)
print("Updating schedule information every " +
      str(sync_delay) + " seconds..")
scheduler.start()
