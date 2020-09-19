import datetime
import time
import requests
import json
from apscheduler.schedulers.blocking import BlockingScheduler
from plyer import notification

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
    else:
        error_msg = "Couldn't authenticate the access token! Make sure the credentials are right!\nSchool code: {0}\nAuth code (without spaces!): {1}".format(
            organization, auth_code)

        print(error_msg)
        send_notification("Couldn't Authenticate!", error_msg)


def get_schedule_updates():
    datum_start = "01/09/2020"
    datum_stop = "30/09/2020"
    timestamp_start = time.mktime(datetime.datetime.strptime(
        datum_start, "%d/%m/%Y").timetuple())
    timestamp_end = time.mktime(datetime.datetime.strptime(
        datum_stop, "%d/%m/%Y").timetuple())

    json_response = requests.get(endpoint + "appointments?user="+user_name+"&access_token="+access_token +
                                 "&start="+str(int(timestamp_start))+"&end="+str(int(timestamp_end))+"&valid=true").json()
    appointments = json_response['response']['data']

    def start_field(appointment):
        return int()

    appointments.sort(key=start_field)

    def time_string(timestamp):
        return datetime.datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')

    for appointment in appointments:
        print(time_string(appointment['start'])+" "+str(appointment['startTimeSlot'])+" "+",".join(
            appointment['teachers']) + " " + ','.join(appointment['subjects']) + " " + ','.join(appointment['locations']))


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
