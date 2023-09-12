import os
import re
import datetime

import requests as rq
import locale
import random
import pytz
import json
from icalendar import Calendar
from icalendar.cal import Component
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus.flowables import KeepInFrame
from dateutil.rrule import rrulestr
from typing import Dict, Callable, Type, TypeVar, Optional, Union, List, Any

# TypeVar to be used in type hints
_T = TypeVar("_T")

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

# Default layout of the document
DOC_LAYOUT = {
    "pagesize": landscape(A4),
    "leftMargin": (6.35 * mm),
    "rightMargin": (6.35 * mm),
    "topMargin": (6.35 * mm),
    "bottomMargin": (6.35 * mm),
}

# The default event location
DEFAULT_LOCATION = 'Queerreferat an den Aachener Hochschulen e.V., Gerlachstraße 20-22, 52064 Aachen, Deutschland'

# Message for a week without events
NO_EVENTS_MSG = "Diese Woche keine Veranstaltungen<br/><i>No events this week</i>"

# Timezone to be considered
LOCAL_TIMEZONE = pytz.timezone('Europe/Berlin')

# Font size of the cells
CELL_FONT_SIZE = 12


class LanguageField:
    """
    Represents an entry that has a corresponding translation
    """

    def __init__(self, ger_val: str, en_val: Optional[str] = None):
        """
        Creates a new LanguageField.
        :param ger_val: The german text.
        :param en_val: The english text.
        """
        self.ger_val = ger_val
        # Set the eng_val to the ger_val if there is no corresponding translation
        # todo there is prob. a better way
        self.en_val = en_val if en_val else ger_val

    @classmethod
    def from_description(cls, description: str):
        description = re.sub(r"<(?!br/).*?>", '', description)
        return cls(
            *(description.split(LANG_DELIMITER_1) if LANG_DELIMITER_1 in description else
              description.split(LANG_DELIMITER_2) if LANG_DELIMITER_2 in description else
              description.split(LANG_DELIMITER_3))
        )

    @classmethod
    def from_translation(cls, ger_val: str, translation_dict: Dict[str, str]):
        return cls(ger_val, translation_dict[ger_val] if ger_val in translation_dict else None)


class CalendarEvent:
    """
    Models an event in the calendar.
    """

    def __init__(self, title: LanguageField,
                 dt_start,
                 dt_end,
                 description: LanguageField,
                 name: str,
                 uid: Any,  # TODO what is this
                 location: str,
                 last_modified: str,
                 rrule: Optional[Any] = None):
        self.title = title
        self.dt_start = dt_start
        self.dt_end = dt_end
        self.description = description
        self.name = name
        self.uid = uid
        self.location = location
        self.last_modified = last_modified
        self.rrule = rrule

    @classmethod
    def from_event(cls, event: Component, translation_dict: Dict[str, str]):
        """
        Creates a CalendarEvent from an existing event.
        :param event: The event
        :param translation_dict: The translation dictionary
        :return: A new CalendarEvent instance.
        """

        # todo is this always possible?
        #   is <>.time() the same as <>.date() (prob not)
        dt_start = event.decoded("DTSTART").date() \
            if isinstance(event.decoded("DTSTART"), datetime.datetime) else \
            event.decoded("DTSTART")

        dt_end = event.decoded("DTEND").date() \
            if isinstance(event.decoded("DTEND"), datetime.datetime) else \
            event.decoded("DTEND")

        return cls(
            LanguageField.from_translation(event.get("SUMMARY"), translation_dict),
            dt_start,
            dt_end,
            LanguageField.from_description(event.get("DESCRIPTION")),
            event.get("NAME"),
            event.get("UID"),
            event.get("LOCATION"),
            event.decoded("LASTMODIFIED"),
            event.get('RRULE').to_ical().decode('utf-8') if event.has_key("RRULE") else None
        )

    def __lt__(self, other):
        """
        Implement the '<' comparison operator.
        """
        return self.dt_start < other.dt_start or \
               (self.dt_start == other.dt_start and self.description < other.description)

    def to_cell(self, lang_ger: bool):
        event_title = self.title.ger_val if lang_ger else self.description.en_val
        event_time = f"{self.dt_start.astimezone(LOCAL_TIMEZONE).strftime('%H:%M')} - " \
                     f"{self.dt_end.astimezone(LOCAL_TIMEZONE).strftime('%H:%M')} "
        event_location = self.location if self.location != DEFAULT_LOCATION else ''
        event_description = self.description.ger_val if lang_ger else self.description.en_val

        return f"""
        <b>{event_title}</b>
        {event_time}
        <i>{event_location}</i>
        {event_description}
        """


def load_json(path: str, modification_fun: Optional[Callable[[str], Type[_T]]] = None) -> Dict[str, Union[str, _T]]:
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


def filter_events(events: List[CalendarEvent]):
    """
    Filter duplicates.
    :param events: A list of events.
    :return: A list of events without duplicates.
    """
    filtered_events = []
    processed_event_uids = set()
    for event in events:
        if event.uid not in processed_event_uids:
            filtered_events.append(event)
            processed_event_uids.add(event.uid)
        else:
            existing_event_index = next(
                (index for index, e in enumerate(filtered_events) if e.uid == event.uid), None
            )

            if existing_event_index is not None:
                existing_event = filtered_events[existing_event_index]

                if event.last_modified > existing_event.last_modified:
                    filtered_events[existing_event_index] = event
    return filtered_events


def main():
    # Output directory and name
    current_directory = os.getcwd()
    current_week = datetime.datetime.now().strftime('%Y-%W')

    # Parse colors that are already set
    event_color_mapping = load_json("data/colors.json", lambda x: colors.HexColor(x))

    # Parse translations
    translation_mapping = load_json("data/translations.json")

    # List of colors that are not set
    tmp_colors = {}

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

            c_event = CalendarEvent.from_event(event, translation_mapping)
            # Regular event
            if c_event.name == 'VEVENT':

                if start_of_week <= c_event.dt_start <= end_of_week:
                    events_of_week.append(c_event)

                # Recurring event
                # TODO what does this do
                if c_event.rrule:
                    recurring_events = []
                    # Create the recurrence rule object from the RRULE string
                    rule = rrulestr(c_event.rrule, dtstart=c_event.dt_start, ignoretz=True)

                    # Convert start_of_week and end_of_week to datetime.datetime objects
                    start_of_week_datetime = datetime.datetime.combine(start_of_week, datetime.datetime.min.time())
                    end_of_week_datetime = datetime.datetime.combine(end_of_week, datetime.datetime.max.time())

                    # Generate the recurring dates within the specified week
                    recurring_dates = rule.between(start_of_week_datetime, end_of_week_datetime, inc=True)

                    for date in recurring_dates:
                        event_start_time = c_event.dt_start.time() \
                            if isinstance(c_event.dt_start, datetime.datetime) else \
                            c_event.dt_start

                        event_end_time = c_event.dt_end.time() \
                            if isinstance(c_event.dt_end, datetime.datetime) else \
                            c_event.dt_end
                        # Calculate the adjusted start and end times based on the original event's duration
                        new_event_start = datetime.datetime.combine(date, event_start_time)
                        new_event_end = datetime.datetime.combine(date, event_end_time)
                        new_event = CalendarEvent(
                            title=c_event.title,
                            description=c_event.description,
                            rrule=c_event.rrule,
                            name=c_event.name,
                            dt_start=new_event_start,
                            dt_end=new_event_end,
                            uid=c_event.uid,
                            location=c_event.location,
                            last_modified=c_event.last_modified
                        )

                        # Convert UNTIL value to UTC if it is timezone-aware
                        # TODO what does this do
                        if 'RRULE' in new_event and 'UNTIL' in new_event['RRULE']:
                            until_value = new_event['RRULE']['UNTIL']
                            if isinstance(until_value, list):
                                until_value = until_value[0]
                            if until_value.tzinfo is not None:
                                until_value = until_value.astimezone(pytz.UTC)
                                new_event['RRULE']['UNTIL'] = [until_value]

                        recurring_events.append(CalendarEvent.from_event(new_event))

                    events_of_week.extend(recurring_events)

        data = [header]

        # Create a dictionary to store events by date
        events_by_date = {date: sorted([event for event in filter_events(events_of_week)
                                        if event.dt_start == date and event.title])
                          for date in dates}

        # Find the highest amount of events
        row_amount = max([len(events_by_date[date]) for date in dates])

        # Create columns for the table
        for j in range(row_amount):
            data.append(['', '', '', '', '', '', ''])
        # TODO 💀👇
        for date in dates:
            events = events_by_date[date]
            k = 1

            for event in sorted(events):
                # Format event information

                styles = getSampleStyleSheet()
                cell_style = styles["BodyText"]
                cell_style.fontSize = CELL_FONT_SIZE
                cell_content = Paragraph(event.to_cell(not t), cell_style)

                data[k][(event.dt_start - start_of_week).days] = cell_content

                k = k + 1
        # Add merged cell coordinates to table style
        for row_index, row in enumerate(data):
            for col_index, cell in enumerate(row):
                # Extract the actual cell content from the KeepInFrame object
                cell_content = cell
                # Extract the first line (bolded) from the cell contents
                cell_content_lines = re.findall(r"<b>(.*?)</b>", str(cell_content))
                event_name = cell_content_lines[0].strip() if cell_content_lines else ''

                if event_name not in event_color_mapping and event_name not in tmp_colors:
                    tmp_colors[event_name] = (random.uniform(0.7, 1), random.uniform(0.7, 1), random.uniform(0.7, 1))

                rowheights = 470 / row_amount
                color_to_use = event_color_mapping.get(event_name) if event_color_mapping.get(
                    event_name) else tmp_colors.get(event_name)
                if 0 < row_index < row_amount:
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
        if row_amount >= 1:
            # Calculate cell heights based on content
            row_heights = [cm * 1.5] + [rowheights] * row_amount
            table = Table(data, colWidths=COLUMN_WIDTH, rowHeights=row_heights)
            table.setStyle(TableStyle(TABLE_STYLE))
            elements.append(table)
        else:
            msg_style = getSampleStyleSheet()["Heading1"]
            msg = Paragraph(NO_EVENTS_MSG, msg_style)
            elements.append(Spacer(1, 2 * cm))
            elements.append(msg)

        # Create the PDF file
        doc = SimpleDocTemplate(output_path, **DOC_LAYOUT)

        # Build the document with the elements
        doc.build(elements)

        print(f'Event overview table generated: {output_path}')


if __name__ == "__main__":
    main()
