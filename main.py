import os
import re
import datetime
import requests as rq
import locale
import random
import pytz
import json
from icalendar import Calendar
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus.flowables import KeepInFrame
from dateutil.rrule import rrulestr
from typing import Dict, Callable, Any

# Delimiters that separate different translations in the ical description
LANG_DELIMITER_1 = "----"
LANG_DELIMITER_2 = "_______________"
LANG_DELIMITER_3 = "______________"

# Width of a column
COLUMN_WIDTH = 110

# Base-style for the table
TABLE_STYLE = [
    ('BACKGROUND', (0, 0), (-1, 0), colors.white),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 14),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 2),
    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
    ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ('SPAN', (0, 1), (0, 2))
]


class LanguageField:
    """
    Represents an entry that has a corresponding translation
    """

    def __init__(self, ger_val: str, en_val: str):
        """
        Creates a new LanguageField.
        :param ger_val: The german text.
        :param en_val: The english text.
        """
        self.ger_val = ger_val
        self.en_val = en_val


class CalendarEvent:
    """
    Models an event in the calendar.
    """

    def __int__(self, event_name: LanguageField, event_start, event_end, event_description: LanguageField):
        self.event_name = event_name
        self.event_start = event_start
        self.event_end = event_end
        self.event_description = event_description


def load_json(path: str, modification_fun: Callable[[str], Any] = None) -> Dict[str, Any]:
    """
    Loads a given json file and modifies its values.
    :param path: The relative path to the json file.
    :param modification_fun: A function which is applied to all values.
    :return: A dictionary containing the (modified) data from the json file.
    """
    with open(path, "r") as file:
        data = json.load(file)
    return data if modification_fun is None \
        else {key: modification_fun(val) for key, val in data.items()}


def fetch_calendar(ical_url: str) -> Calendar:
    """
    Fetches the calendar from the given url and parses it to a calendar object.
    :param ical_url: The url to the ical.
    :return: A parsed calendar.
    """
    response = rq.get(ical_url)
    if response.status_code != 200:
        print('Failed to fetch iCal data.')
        exit(1)
    return Calendar.from_ical(response.text)


def main():
    location_variable = 'Queerreferat an den Aachener Hochschulen e.V., Gerlachstraße 20-22, 52064 Aachen, Deutschland'

    # Output directory and name
    current_directory = os.getcwd()
    current_week = datetime.datetime.now().strftime('%Y-%W')

    # List of colors that are not set
    tmp_colors = {}
    event_color_mapping = load_json("data/colors.json", lambda x: colors.HexColor(x))

    # Set the local timezone
    local_timezone = pytz.timezone('Europe/Berlin')

    calendar = fetch_calendar(
        'https://calendar.google.com/calendar/ical/queerreferat.aachen%40gmail.com/public/basic.ics'
    )

    # Get the date scopes
    current_date = datetime.datetime.now().date()
    start_of_week = current_date - datetime.timedelta(days=current_date.weekday())
    end_of_week = start_of_week + datetime.timedelta(days=6)

    # Prepare column Headers
    header = []
    dates = [start_of_week + datetime.timedelta(days=i) for i in range(7)]
    header.extend(date.strftime('%A\n%d %b') for date in dates)

    # TODO:
    #   Steps:
    #       1. Parsing
    #       2. Generating
    #   Dont do this 👇👇
    for t in range(2):
        # Define the output directory and filename
        try:
            locale.setlocale(locale.LC_TIME, "de_DE.utf8" if not t else "en_US.utf8")
        except locale.Error:
            print("Unsupported locale setting, using default locale.")

        output_filename = f'event_overview_{current_week}_{"de" if not t else "en"}.pdf'

        output_path = os.path.join(current_directory, output_filename)

        # Remove the file if it already exists
        if os.path.exists(output_path):
            os.remove(output_path)

        events_of_week = []

        # Iterate over the events in the calendar
        for event in calendar.walk():
            if event.name == 'VEVENT':
                # Regular event
                event_start = event.decoded('DTSTART')
                if isinstance(event_start, datetime.datetime):
                    event_start = event_start.date()
                event_end = event.decoded('DTEND')
                if isinstance(event_end, datetime.datetime):
                    event_end = event_end.date()

                if start_of_week <= event_start <= end_of_week or start_of_week <= event_end <= end_of_week:
                    events_of_week.append(event)

                # Recurring event
                if event.get('RRULE'):
                    rrule = event['RRULE'].to_ical().decode('utf-8')

                    recurring_events = []

                    # Create the recurrence rule object from the RRULE string
                    rule = rrulestr(rrule, dtstart=event_start, ignoretz=True)

                    # Convert start_of_week and end_of_week to datetime.datetime objects
                    start_of_week_datetime = datetime.datetime.combine(start_of_week, datetime.datetime.min.time())
                    end_of_week_datetime = datetime.datetime.combine(end_of_week, datetime.datetime.max.time())

                    # Generate the recurring dates within the specified week
                    recurring_dates = rule.between(start_of_week_datetime, end_of_week_datetime, inc=True)

                    for date in recurring_dates:
                        new_event = event.copy()

                        event_start_time = event.decoded('DTSTART')
                        if isinstance(event_start_time, datetime.datetime):
                            event_start_time = event_start_time.time()
                        event_end_time = event.decoded('DTEND')
                        if isinstance(event_end_time, datetime.datetime):
                            event_end_time = event_end_time.time()

                        # Calculate the adjusted start and end times based on the original event's duration
                        new_event_start = datetime.datetime.combine(date, event_start_time)
                        new_event_end = datetime.datetime.combine(date, event_end_time)

                        new_event['DTSTART'].dt = new_event_start
                        new_event['DTEND'].dt = new_event_end

                        # Convert UNTIL value to UTC if it is timezone-aware
                        if 'RRULE' in new_event and 'UNTIL' in new_event['RRULE']:
                            until_value = new_event['RRULE']['UNTIL']
                            if isinstance(until_value, list):
                                until_value = until_value[0]
                            if until_value.tzinfo is not None:
                                until_value = until_value.astimezone(pytz.UTC)
                                new_event['RRULE']['UNTIL'] = [until_value]

                        recurring_events.append(new_event)

                    events_of_week.extend(recurring_events)

        data = [header]

        # Create a dictionary to store events by date
        events_by_date = {date: [] for date in dates}

        # Filtering duplicate events:
        filtered_events = []
        processed_event_uids = set()

        for event in events_of_week:
            event_uid = event.get('UID')

            if event_uid not in processed_event_uids:
                filtered_events.append(event)
                processed_event_uids.add(event_uid)
            else:
                existing_event_index = next(
                    (index for index, e in enumerate(filtered_events) if e.get('UID') == event_uid), None
                )

                if existing_event_index is not None:
                    existing_event = filtered_events[existing_event_index]

                    if event.decoded('LAST-MODIFIED') > existing_event.decoded('LAST-MODIFIED'):
                        filtered_events[existing_event_index] = event

        events_of_week = filtered_events

        # Group events by date
        for event in events_of_week:
            event_start = event.decoded('DTSTART')
            if isinstance(event_start, datetime.datetime):
                event_start = event_start.date()
            # Filter events if needed
            if event.decoded('SUMMARY') != bytes('', 'utf-8'):
                events_by_date[event_start].append(event)

        # Find highest amount of events
        row_amount = max([len(events_by_date[date]) for date in dates])

        # Create columns for the table
        for j in range(row_amount):
            data.append(['', '', '', '', '', '', ''])
        # TODO 💀👇
        for date in dates:
            events = events_by_date[date]
            k = 1

            events = sorted(events, key=lambda e: e.decoded('DTSTART').astimezone(local_timezone))
            sorted_events = []
            for (index, ev) in enumerate(events):
                if ev in sorted_events:
                    continue
                if index != len(events) - 1 and ev.decoded('DTSTART').astimezone(local_timezone) == events[
                    index + 1].decoded('DTSTART').astimezone(local_timezone) and ev.get("SUMMARY") > events[
                    index + 1].get(
                    "SUMMARY"):
                    sorted_events.append(events[index + 1])
                    sorted_events.append(ev)
                else:
                    sorted_events.append(ev)

            for event in sorted_events:
                # Format event information
                event_title = event.get('SUMMARY')
                event_time = f"{event.decoded('DTSTART').astimezone(local_timezone).strftime('%H:%M')} - {event.decoded('DTEND').astimezone(local_timezone).strftime('%H:%M')}"
                event_location = "<br/>" + event.get('LOCATION', '') if event.get('LOCATION',
                                                                                  '') != location_variable else ''
                event_description = re.sub(r'<(?!br/).*?>', '', event.get('DESCRIPTION', ''))
                event_description = event_description.split(LANG_DELIMITER_1)[t] \
                    if LANG_DELIMITER_1 in event_description \
                    else event_description.split(LANG_DELIMITER_2)[t] \
                    if LANG_DELIMITER_2 in event_description \
                    else event_description.split(LANG_DELIMITER_3)[t]

                styles = getSampleStyleSheet()
                cell_style = styles["BodyText"]
                cell_style.fontSize = 12

                # Collect event infos
                cell_contents = f"<b>{event_title}</b><br/>{event_time}<i>{event_location}</i><br/>{event_description}"
                cell_content = Paragraph(cell_contents, cell_style)

                event_start = event.decoded('DTSTART')
                if isinstance(event_start, datetime.datetime):
                    event_start = event_start.date()

                data[k][(event_start - start_of_week).days] = cell_content

                k = k + 1

        # Add merged cell coordinates to table style
        for row_index, row in enumerate(data):
            for col_index, cell in enumerate(row):
                # Extract the actual cell content from the KeepInFrame object
                # cell_content = cell._content[0] if isinstance(cell, KeepInFrame) else cell
                cell_content = cell
                # Extract the first line (bolded) from the cell contents
                cell_content_lines = re.findall(r"<b>(.*?)</b>", str(cell_content))
                event_name = cell_content_lines[0].strip() if cell_content_lines else ''

                if event_name not in event_color_mapping and event_name not in tmp_colors:
                    tmp_colors[event_name] = (random.uniform(0.7, 1), random.uniform(0.7, 1), random.uniform(0.7, 1))

                rowheights = 470 / row_amount
                color_to_use = event_color_mapping.get(event_name) if event_color_mapping.get(
                    event_name) else tmp_colors.get(event_name)
                if row_index > 0 and row_index < row_amount:
                    if data[row_index][col_index] != '':
                        TABLE_STYLE.append(('BACKGROUND', (col_index, row_index), (col_index, row_index), color_to_use))
                    if data[row_index + 1][col_index] == '':
                        if row_index + 2 <= row_amount and data[row_index + 2][col_index] == '':
                            TABLE_STYLE.append(('SPAN', (col_index, row_index), (col_index, row_index + 2)))
                            rowheights = 3 * rowheights
                            if data[row_index][col_index] != '':
                                TABLE_STYLE.append(
                                    ('BACKGROUND', (col_index, row_index), (col_index, row_index + 2), color_to_use))
                        else:
                            TABLE_STYLE.append(('SPAN', (col_index, row_index), (col_index, row_index + 1)))
                            rowheights = 2 * rowheights
                            if data[row_index][col_index] != '':
                                TABLE_STYLE.append(
                                    ('BACKGROUND', (col_index, row_index), (col_index, row_index + 1), color_to_use))

                elif row_index == row_amount and data[row_index][col_index] != '':
                    TABLE_STYLE.append(('BACKGROUND', (col_index, row_index), (col_index, row_index), color_to_use))

                if type(cell_content) == Paragraph:
                    cell_content = KeepInFrame(COLUMN_WIDTH, rowheights, [cell_content])
                    data[row_index][col_index] = cell_content

        elements = []

        # Add title
        title_style = getSampleStyleSheet()["Title"]
        if t == 0:
            title_text = f"Veranstaltungen der Woche vom {start_of_week.strftime('%d %b %Y')} bis {end_of_week.strftime('%d %b %Y')}"
        else:
            title_text = f"<i>Events of the week from {start_of_week.strftime('%d %b %Y')} to {end_of_week.strftime('%d %b %Y')}</i>"

        title = Paragraph(title_text, title_style)
        elements.append(title)

        # Create table
        # TODO ??????? 👇👇👇👇👇🤔🤔🤔
        if row_amount < 1:
            # Calculate cell heights based on content
            row_heights = [cm * 1.5] + [rowheights] * row_amount
            table = Table(data, colWidths=COLUMN_WIDTH, rowHeights=row_heights)
            table.setStyle(TableStyle(TABLE_STYLE))
            elements.append(table)
        else:
            msg_style = getSampleStyleSheet()["Heading1"]
            msg_text = "Diese Woche keine Veranstaltungen<br/><i>No events this week</i>"
            msg = Paragraph(msg_text, msg_style)
            elements.append(Spacer(1, 2 * cm))
            elements.append(msg)

        # Create the PDF file
        doc = SimpleDocTemplate(output_path, pagesize=landscape(A4), leftMargin=(6.35 * mm), rightMargin=(6.35 * mm),
                                topMargin=(6.35 * mm),
                                bottomMargin=(6.35 * mm))

        # Build the document with the elements
        doc.build(elements)

        print(f'Event overview table generated: {output_path}')


if __name__ == "__main__":
    main()
