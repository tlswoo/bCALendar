from __future__ import print_function
import sys
sys.path.insert(0, './packages')
import datetime, webbrowser
from googleapiclient.discovery import build
from httplib2 import Http
from selenium import webdriver
from oauth2client import file, client, tools
import CalendarEvents
SCOPES = 'https://www.googleapis.com/auth/calendar'

def main():
    store = file.Storage('token.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('calendar', 'v3', http=creds.authorize(Http()))

    # Get all classes from the downloaded file
    print("Creating new calendar...")
    calendar = {
        'summary': "Classes added from CALendar",
        'timeZone': 'America/Los_Angeles'
    }
    created_calendar = service.calendars().insert(body=calendar).execute()
    calendar_id = created_calendar['id']
    print("Done!")

    print("Please log into CalCentral.")
    driver = webdriver.Firefox(executable_path=r'./geckodriver.exe') # Firefox webdriver

    login_url = "https://auth.berkeley.edu/cas/login?service=https%3A%2F%2Fcalcentral.berkeley.edu%2Fauth%2Fcas%2Fcallback%3Furl%3Dhttps%253A%252F%252Fcalcentral.berkeley.edu%252Facademics"
    driver.get(login_url)
    while driver.current_url == login_url:
        continue
    driver.get("https://calcentral.berkeley.edu/college_scheduler/student/UGRD/2192")
    schedule_planner = driver.page_source
    print("Getting classes...")
    ScheduleObj = CalendarEvents.ScheduleTableReader(schedule_planner)
    for class_name in ScheduleObj.classes.keys():
        choice = input("Would you like to add {0} to your Google Calendar? Y/N ".format(class_name)).upper()
        while choice != "Y" and choice != "N":
            choice = input("Invalid input. Please select Y/N")
        if choice == 'Y':
            temp_class = ScheduleObj.classes.get(class_name)
            event = {
                'summary': temp_class.header_string(),
                'location': temp_class.location.location_url,
                'description': 'Class: {0}\n' + ('Instructors: {1}'.format(temp_class.header_string(), temp_class.instructor_string())) if temp_class.instructor_string() else "No instructors found",
                'start': {
                    'dateTime': temp_class.start_date[:11] + temp_class.time_range.get_string_time('start'),
                    'timeZone': 'America/Los_Angeles',
                },
                'end': {
                    'dateTime': temp_class.start_date[:11] + temp_class.time_range.get_string_time('end'),
                    'timeZone': 'America/Los_Angeles',
                },
                'recurrence': [
                    "RRULE:FREQ=WEEKLY;UNTIL=" + temp_class.end_date[:10].replace("-", "") + ";BYDAY=" + str(temp_class.days)[1:-1].replace(" ", "").replace("'", "")
                ],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                    {'method': 'popup', 'minutes': 30},
                    ],
                },
            }
            event = service.events().insert(calendarId=calendar_id, body=event).execute()
            print("Added!")
        else:
            continue
            # @TODO add yes or no choices, insert a new calendar to put the classes into, prompt user for input, add individual classes, confirmation before adding class, double check authentication

if __name__ == "__main__": main()
