#!/usr/in/env python3
import textract

WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']


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
                if line == '':
                    # TODO: This will not work if there is an empty day in the
                    # middle of the week
                    # '' marks the end of a set of daily start and end times
                    nextLineIsTime = False
                else:
                    # Parse the start and end times from the line
                    dayTimes = line.split(' - ')
                    # The list of times always go from Monday -> Friday, so the
                    # first parsed line is for Monday, the next for Tuesday etc
                    weekdayNumber = line_num - firstLineWithTimes
                    # Add a new day to the last week in the schedule
                    schedule[-1].addWeekDay(day(WEEKDAYS[weekdayNumber],
                                                dayTimes[0], dayTimes[1]))
                continue
            if 'Tid 1' in line:
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
            print('\n------------- WEEK {} -------------'.format(weekObj.weekNumber))
            print('|  Weekday  | StartTime | EndTime |')
            print('|---------------------------------|')
            for dayObj in weekObj.days:
                pprWeekday = '| ' + dayObj.weekday + \
                    ' '*(10 - len(dayObj.weekday))
                pprStartTime = '|   {}   '.format(dayObj.startTime)
                pprEndTime = '|  {}  |'.format(dayObj.endTime)
                print(pprWeekday + pprStartTime + pprEndTime)
            print('-----------------------------------')


if __name__ == "__main__":
    parser = pdfParser(pdfFile="Nytt schema.pdf", firstWeekNumber=44)
    print("Parsing pdf")
    schedule = parser.parsePdf()
    print("\nSchedule parsed from pdf:")
    parser.prettyPrintWeeks(schedule)
    # TODO: Add code for writing to google calendar
