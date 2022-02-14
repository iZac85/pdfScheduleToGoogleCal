#!/usr/in/env python3
import textract
import os.path
import yaml
import datetime
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from pathlib import Path


class day:
    def __init__(self, weekday, startTime, endTime):
        self.weekday = weekday
        self.startTime = startTime
        self.endTime = endTime


class week:
    def __init__(self, weekNumber):
        self.weekNumber = weekNumber
        self.days = []

    def addWeekDay(self, day):
        # Add a day object to the end of the list of days
        self.days.append(day)


class pdfParser:
    def __init__(self, pdfFile, firstWeekNumber):
        self._pdfFile = pdfFile
        self._firstWeekNumber = firstWeekNumber
        self.WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    def parsePdf(self):
        schedule = []
        # Read text from the supplied PDF
        rawText = textract.process(self._pdfFile)
        text = rawText.decode("utf-8")
        lines = text.splitlines()
        nextLineIsTime = False
        firstLineWithTimes = -1
        weekCounter = 0
        # Loop through the lines from the parsed pdf
        for line_num, line in enumerate(lines):
            if nextLineIsTime:
                if line == "":
                    # TODO: This will not work if there is an empty day in the
                    # middle of the week
                    # '' marks the end of a set of daily start and end times
                    nextLineIsTime = False
                else:
                    # Parse the start and end times from the line
                    dayTimes = line.split(" - ")
                    # The list of times always go from Monday -> Friday, so the
                    # first parsed line is for Monday, the next for Tuesday etc
                    weekdayNumber = line_num - firstLineWithTimes
                    # Add a new day to the last week in the schedule
                    schedule[-1].addWeekDay(
                        day(self.WEEKDAYS[weekdayNumber], dayTimes[0], dayTimes[1])
                    )
                continue
            if "Tid 1" in line:
                # Tid 1 marks the last row before a set of daily start and end
                # times for a new week
                nextLineIsTime = True
                firstLineWithTimes = line_num + 1
                # Add a new week to the schedule and give it a week number
                schedule.append(week(self._firstWeekNumber + weekCounter))
                weekCounter += 1
        return schedule

    def prettyPrintWeeks(self, schedule):
        """
        # prettyPrintWeeks

        Function that takes in a schedule and prints it in a readable way

        """
        for weekObj in schedule:
            print("\n------------- WEEK {} -------------".format(weekObj.weekNumber))
            print("|  Weekday  | StartTime | EndTime |")
            print("|---------------------------------|")
            for dayObj in weekObj.days:
                pprWeekday = "| " + dayObj.weekday + " " * (10 - len(dayObj.weekday))
                pprStartTime = "|   {}   ".format(dayObj.startTime)
                pprEndTime = "|  {}  |".format(dayObj.endTime)
                print(pprWeekday + pprStartTime + pprEndTime)
            print("-----------------------------------")


class googleCalendarApi:
    def __init__(self) -> None:
        self.get_settings()
        # If modifying these scopes, delete the file token.json.
        self.SCOPES = [self.settings["googleCalendarLink"]]

    def connect(self):
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", self.SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open("token.json", "w") as token:
                token.write(creds.to_json())
        self.service = build("calendar", "v3", credentials=creds)

    def get_calendar_details(self):
        """Shows basic usage of the Google Calendar API.
        Prints the start and name of the next 10 events on the user's calendar.
        """
        # Get details for the calendar
        calendar_details = (
            self.service.calendars()
            .get(calendarId=self.settings["calendarId"])
            .execute()
        )
        print("Summary: {}".format(calendar_details["summary"]))
        print("Description: {}".format(calendar_details["description"]))

    def write_to_calendar(self):
        """Shows basic usage of the Google Calendar API.
        Prints the start and name of the next 10 events on the user's calendar.
        """
        # TODO: Add code for writing to google calendar
        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time

        print("Getting the upcoming 10 events")
        events_result = (
            self.service.events()
            .list(
                calendarId=self.settings["calendarId"],
                timeMin=now,
                maxResults=10,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            print("No upcoming events found.")
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            print(start, event["summary"])

    def get_settings(self):
        """
        # get_settings

        Function that returns a dict with settings read from a yaml-file
        """
        full_file_path = Path(__file__).parent.joinpath("settings.yaml")
        with open(full_file_path) as settings:
            self.settings = yaml.load(settings, Loader=yaml.Loader)


if __name__ == "__main__":
    parser = pdfParser(pdfFile="Nytt schema.pdf", firstWeekNumber=5)
    print("=========== Parsing pdf ===========")
    schedule = parser.parsePdf()
    print("\nSchedule parsed from pdf:")
    parser.prettyPrintWeeks(schedule)
    print("\n=========== Connecting to Google Calendar ===========")
    googleCalApi = googleCalendarApi()
    googleCalApi.connect()
    googleCalApi.get_calendar_details()
    print("\n=========== Writing schedule to Google Calendar ===========")
    googleCalApi.write_to_calendar()
