import os
import re
import datetime
from copy import deepcopy

import requests as rq
import locale
import pytz
import json
from icalendar import Calendar
from icalendar.cal import Component
from reportlab.lib import colors
from dateutil.rrule import rrulestr
from typing import Dict, Callable, Type, TypeVar, Optional, Union, List, Any

# TypeVar to be used in type hints
_T = TypeVar("_T")

# Delimiters that separate different translations in the ical description
REGEX_DELIMITER = r'[-_]{3,}'

# The default event location
DEFAULT_LOCATION = 'Queerreferat an den Aachener Hochschulen e.V., Gerlachstraße 20-22, 52064 Aachen, Deutschland'

# Message for a week without events
NO_EVENTS_MSG = "Diese Woche keine Veranstaltungen<br/><i>No events this week</i>"

# Timezone to be considered
LOCAL_TIMEZONE = pytz.timezone('Europe/Berlin')



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
        """
        Creates a LanguageField from the body of a calendar event. Assumes there is a delimiter
        in form of "---<...>" or "___<...>"
        :param description: The description of the calendar event.
        :return: A LanguageField with the corresponding german and english values.
        """
        description = re.sub(r"<(?!br/).*?>", '', description)
        splits = re.split(REGEX_DELIMITER, description)
        return cls(
            *(splits if re.search(REGEX_DELIMITER, description) and len(splits) == 2 else
              [description, description])
        )

    @classmethod
    def from_translation(cls, ger_val: str, translation_dict: Dict[str, str]):
        """
        Creates a LanguageField from the translation entry.
        :param ger_val: The german value of this field.
        :param translation_dict: The translation dictionary.
        :return: A LanguageField with the german and corresponding english value
        """
        return cls(ger_val, translation_dict[ger_val] if ger_val in translation_dict else ger_val)


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

        return cls(
            LanguageField.from_translation(event.get("SUMMARY"), translation_dict),
            event.decoded("DTSTART"),
            event.decoded("DTEND"),
            LanguageField.from_description(event.get("DESCRIPTION", "")),
            event.get("NAME"),
            event.get("UID"),
            event.get("LOCATION"),
            event.decoded("LAST-MODIFIED"),
            event.get('RRULE').to_ical().decode('utf-8') if "RRULE" in event else None
        )

    def __lt__(self, other):
        """
        Implement the '<' comparison operator.
        """
        return self.dt_start < other.dt_start or \
               (self.dt_start == other.dt_start and self.description < other.description)

    def get_start_date(self):
        """
        Returns the start date of a calendar event.
        :return: The start date
        """
        return self.dt_start.date() if isinstance(self.dt_start, datetime.datetime) \
            else self.dt_start

    def to_cell(self, lang_ger: bool):
        if not lang_ger:
            pass        # todo
        event_title = self.title.ger_val if lang_ger else self.title.en_val
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
    """
    Creates the event plan for the current week.
    """
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
        i = 0
        # Iterate over the events in the calendar
        for event in calendar.walk():
            # Regular event
            if event.name == 'VEVENT':
                # Check whether the event is cancelled
                # if "EXDATE" in event:
                #    continue
                i += 1

                if i == 194:
                    print(event)
                c_event = CalendarEvent.from_event(event, translation_mapping)

                dt_start = c_event.get_start_date()

                if start_of_week <= dt_start <= end_of_week:
                    events_of_week.append(c_event)

                # Recurring event
                if c_event.rrule:
                    recurring_events = []
                    # Create the recurrence rule object from the RRULE string
                    rule = rrulestr(c_event.rrule, dtstart=dt_start, ignoretz=True)

                    # Convert start_of_week and end_of_week to datetime.datetime objects
                    # This is achieved by using e.g. start_of_week (date) and min (time)
                    start_of_week_datetime = datetime.datetime.combine(start_of_week, datetime.datetime.min.time())
                    end_of_week_datetime = datetime.datetime.combine(end_of_week, datetime.datetime.max.time())

                    # Generate the recurring dates within the specified week using our recurrence rule object
                    # all occurrences in current week (based on the rrule)
                    recurring_dates = rule.between(start_of_week_datetime, end_of_week_datetime, inc=True)

                    for date in recurring_dates:
                        event_start_time = c_event.dt_start.time() \
                            if isinstance(c_event.dt_start, datetime.datetime) else \
                            c_event.dt_start

                        event_end_time = c_event.dt_end.time() \
                            if isinstance(c_event.dt_end, datetime.datetime) else \
                            c_event.dt_end

                        new_event = deepcopy(c_event)
                        new_event.dt_start = datetime.datetime.combine(date, event_start_time)
                        new_event.dt_end = datetime.datetime.combine(date, event_end_time)

                        # Convert UNTIL value to UTC if it is timezone-aware
                        # TODO what does this do
                        # todo recurring events seem to be in wrong timezone (utc)
                        if new_event.rrule and 'UNTIL' in new_event.rrule:
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
        events_by_date = {date: sorted([event for event in filter_events(events_of_week)
                                        if event.get_start_date() == date and event.title]) for date in dates}

        # Iteration zB durch...
        for date in events_by_date.keys():
            print(f"Date: {date}:\n")
            for event in events_by_date[date]:
                print(event.to_cell(lang_ger=True) + "\n")


if __name__ == "__main__":
    main()
