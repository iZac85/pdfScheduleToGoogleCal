#!/usr/in/env python3
import logging
import textract
import os.path
import yaml
import re
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from pathlib import Path
from datetime import date, datetime, time

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


class day:
    def __init__(self, weekday, startTime, endTime):
        self.weekday = weekday
        self.startTime = startTime
        self.endTime = endTime


class week:
    def __init__(self, weekNumber):
        self.weekNumber = weekNumber
        self.days = []

    def add_week_day(self, day):
        # Add a day object to the end of the list of days
        self.days.append(day)


class pdfParser:
    def __init__(self, pdfFile, firstWeekNumber):
        self._pdfFile = pdfFile
        self._firstWeekNumber = firstWeekNumber

    def parse_pdf(self):
        """
        # parse_pdf

        Parses a pdf containing a schedule. Currently only supports the
        format used by Kungälv municipal

        Returns a list called schedule

        """
        schedule = []
        # Read text from the supplied PDF
        rawText = textract.process(self._pdfFile)
        text = rawText.decode("utf-8")
        lines = text.splitlines()
        firstLineWithTimesFound = False
        weekCounter = 0
        # Loop through the lines from the parsed pdf
        for line in enumerate(lines):
            # Look for lines with timestamps
            if re.search("(\d\d:\d\d - \d\d:\d\d)", line):
                if not firstLineWithTimesFound:
                    # Tid 1 marks the last row before a set of daily start and end
                    # times for a new week
                    firstLineWithTimesFound = True
                    # Add a new week to the schedule and give it a week number
                    schedule.append(week(self._firstWeekNumber + weekCounter))
                    weekCounter += 1
                    weekdayNumber = 0
                # Parse the start and end times from the line
                dayTimes = line.split(" - ")
                # Add a new day to the last week in the schedule
                schedule[-1].add_week_day(
                    day(
                        WEEKDAYS[weekdayNumber],
                        time.fromisoformat(dayTimes[0]),
                        time.fromisoformat(dayTimes[1]),
                    )
                )
                weekdayNumber += 1
            elif line == "-":
                # To handle empty days within a week, the pdf needs to be
                # edited with dashes for empty days.
                # Thus '-' means increase the day counter by one
                weekdayNumber += 1
            elif line == "":
                if schedule != [] and not schedule[-1].days:
                    # If no days have been added, the empty line is NOT the
                    # end of the week schedule. Continue looking until
                    # start- and end-times are found
                    continue
                else:
                    if schedule != []:
                        # '' marks the end of a set of daily start and end times
                        firstLineWithTimesFound = False
        return schedule

    def pretty_print_weeks(self, schedule):
        """
        # pretty_print_weeks

        Function that takes in a schedule and prints it in a readable way

        """
        for weekObj in schedule:
            logging.info(
                "------------- WEEK {} -------------".format(weekObj.weekNumber)
            )
            logging.info("|  Weekday  | StartTime | EndTime |")
            logging.info("|---------------------------------|")
            for dayObj in weekObj.days:
                pprWeekday = "| " + dayObj.weekday + " " * (10 - len(dayObj.weekday))
                pprStartTime = "|   {}   ".format(
                    dayObj.startTime.isoformat(timespec="minutes")
                )
                pprEndTime = "|  {}  |".format(
                    dayObj.endTime.isoformat(timespec="minutes")
                )
                logging.info(pprWeekday + pprStartTime + pprEndTime)
            logging.info("-----------------------------------")


class googleCalendarApi:
    def __init__(self, schedule) -> None:
        self.get_settings()
        # If modifying these scopes, delete the file token.json.
        self.SCOPES = [self.settings["googleCalendarLink"]]
        self.schedule = schedule

    def connect(self):
        """
        # connect

        Connects to the Google Calendar API and creates a service

        """
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
        """
        # get_calendar_details

        Prints details of the calendar specified by the calendarId in settings.yaml

        """
        # Get details for the calendar
        calendar_details = (
            self.service.calendars()
            .get(calendarId=self.settings["calendarId"])
            .execute()
        )
        logging.info("Summary: {}".format(calendar_details["summary"]))
        logging.info("Description: {}".format(calendar_details["description"]))

    def write_to_calendar(self):
        """
        # write_to_calendar

        Loops through the weeks in the schedule list and adds all future events
        to the calendar.

        googleCalendarApi.connect must have been run first.

        """
        today = date.today()
        currentYear = today.year
        currentWeek = today.isocalendar().week

        # Loop through the weeks
        for weekObj in self.schedule:
            if weekObj.weekNumber < currentWeek:
                logging.info(
                    'Schedule week "{}" occurs in the past. Skipping it'.format(
                        weekObj.weekNumber
                    )
                )
                continue
            logging.info(
                'Adding schedule week "{}" to calendar'.format(weekObj.weekNumber)
            )
            for dayObj in weekObj.days:
                dateOfWeekDay = date.fromisocalendar(
                    currentYear, weekObj.weekNumber, WEEKDAYS.index(dayObj.weekday) + 1
                )  # (year, week, day of week)
                if dateOfWeekDay < today:
                    logging.info(
                        'Schedule day "{}" occurs in the past. Skipping it'.format(
                            dateOfWeekDay
                        )
                    )
                    continue
                if (
                    "pickUpDropOff" in self.settings
                    and dayObj.weekday in self.settings["pickUpDropOff"]
                ):
                    description, attendees = self.get_pickUpDropOff_info(
                        self.settings["pickUpDropOff"][dayObj.weekday],
                        weekObj.weekNumber,
                    )
                logging.info("Adding event:")
                logging.info(" -> Date: {} - {}".format(dateOfWeekDay, dayObj.weekday))
                logging.info(" -> Time: {}-{}".format(dayObj.startTime, dayObj.endTime))
                logging.info(" -> Event info: {}".format(repr(description)))
                start = datetime.combine(dateOfWeekDay, dayObj.startTime).isoformat()
                end = datetime.combine(dateOfWeekDay, dayObj.endTime).isoformat()
                self.create_event(start, end, description, attendees)
            logging.info("-----------------------------------")

    def get_settings(self):
        """
        # get_settings

        Function that returns a dict with settings read from a yaml-file

        """
        full_file_path = Path(__file__).parent.joinpath("settings.yaml")
        with open(full_file_path) as settings:
            self.settings = yaml.load(settings, Loader=yaml.Loader)

    def create_event(self, start, end, description, attendees):
        """
        # create_event

        Creates an event in the Calendar.
        Required inputs are: start, end, description, attendees

        """
        event_result = (
            self.service.events()
            .insert(
                calendarId=self.settings["calendarId"],
                body={
                    "summary": "Förskola",
                    "description": description,
                    "start": {
                        "dateTime": start,
                        "timeZone": "Europe/Stockholm",
                    },
                    "end": {"dateTime": end, "timeZone": "Europe/Stockholm"},
                    "attendees": attendees,
                },
            )
            .execute()
        )
        logging.debug("Created event:")
        logging.debug(" - id: {}".format(event_result["id"]))
        logging.debug(" - summary: {}".format(event_result["summary"]))
        logging.debug(" - starts at: {}".format(event_result["start"]["dateTime"]))
        logging.debug(" - ends at: {}".format(event_result["end"]["dateTime"]))
        logging.debug(" - description: {}".format(repr(event_result["description"])))
        if "attendees" in event_result:
            logging.debug(" - attendees: {}".format(event_result["attendees"]))

    @staticmethod
    def get_pickUpDropOff_info(pickUpDropOffInfo, weekNumber):
        """
        # get_pickUpDropOff_info

        Extracts info from the pickUpDropOff-dictionary (specified in settings.yaml)
        Used for adding description and/or attendees to an event

        """
        info = ""
        attendees = []
        for rule in pickUpDropOffInfo:
            if "attendees" in rule:
                attendees = rule["attendees"]
            if not "weeks" in rule:
                logging.warn("Unsupported pickUpDropOff-rule: {}".format(rule))
                continue
            if rule["weeks"] == "all":
                info = rule["info"]
                break
            elif rule["weeks"] == "even":
                if weekNumber % 2 == 0:
                    info = rule["info"]
                    break
            elif rule["weeks"] == "odd":
                if weekNumber % 2 == 1:
                    info = rule["info"]
                    break
            else:
                logging.warn(
                    "Unsupported weeks format in pickUpDropOff-rule: {}".format(
                        rule["weeks"]
                    )
                )
                continue
        return info, attendees


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(message)s")
    parser = pdfParser(pdfFile="Nytt schema.pdf", firstWeekNumber=19)
    logging.info("=========== Parsing pdf ===========")
    schedule = parser.parse_pdf()
    logging.info("Schedule parsed from pdf:")
    parser.pretty_print_weeks(schedule)
    logging.info("=========== Connecting to Google Calendar ===========")
    googleCalApi = googleCalendarApi(schedule)
    googleCalApi.connect()
    googleCalApi.get_calendar_details()
    logging.info("=========== Writing schedule to Google Calendar ===========")
    googleCalApi.write_to_calendar()
