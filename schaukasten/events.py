import re
from enum import StrEnum, auto
from typing import Annotated, Self

import arrow
import recurring_ical_events
from icalendar import Calendar, Event
from pydantic import AfterValidator, BaseModel, PlainSerializer, PlainValidator


class Language(StrEnum):
    ENGLISH = auto()
    GERMAN = auto()


class ICalKeys(StrEnum):
    DTSTART = auto()
    DTEND = auto()
    SUMMARY = auto()
    LOCATION = auto()
    DESCRIPTION = auto()
    VEVENT = auto()


ArrowType = Annotated[
    arrow.Arrow,
    PlainValidator(arrow.get),
    PlainSerializer(lambda time: time.isoformat(), return_type=str),
]


class Event(BaseModel):
    """
    Represents an event with start and end times, title, description, and place. The title and description are dicts with a Language Enum Member as key and the string in that language as value. The place defaults to the Queerreferats Address.
    """

    start: ArrowType
    end: ArrowType
    title: dict[Language, str]
    description: dict[Language, str]
    place: str = "Queerreferat an den Aachener Hochschulen e.V.\nGerlachstr. 20-22\n52064 Aachen, DE"

    @classmethod
    def from_ical(cls: Self, ical_event: Event) -> Self:
        """
        Convert an iCalendar event to a custom event object.

        :param cls: The class object.
        :param ical_event: The iCalendar event to convert.
        :type ical_event: Event
        :return: The converted custom event object.
        :rtype: Self
        """

        # splitting titles on "|" and giving language keys
        titles = [title.trim() for title in ical_event[ICalKeys.SUMMARY].split("|")]
        title_dict = dict(zip(list(Language), titles))

        # removing html markers from description and splitting on triple repetitions of "-" or "-" to languages
        # todo ckeck if necessary
        raw_description_cleaned = re.sub(r"<.*?>", "", ical_event.DESCRIPTION)
        descriptions = re.split(r"[-_]{3,}", raw_description_cleaned)
        description_dict = dict(zip(list(Language), descriptions))

        # constructing event
        return cls(
            start=ical_event.decode(ICalKeys.DTSTART.value),
            end=ical_event.decode(ICalKeys.DTEND.value),
            title=title_dict,
            description=description_dict,
            place=ical_event.get(ICalKeys.LOCATION.value),
        )


class EventSpan(BaseModel):
    start: ArrowType
    end: ArrowType
    events: Annotated[
        list[Event],
        AfterValidator(lambda events: list(sorted(events, key=lambda e: e.start))),
    ]

    @classmethod
    def from_ical(
        cls: Self, cal: Calendar, start: arrow.Arrow, end: arrow.Arrow
    ) -> Self:
        """
        Create an instance of the class from iCalendar data.

        Args:
            cls (type): The class type.
            cal (Calendar): The iCalendar object.
            start (arrow.Arrow): The start date and time.
            end (arrow.Arrow): The end date and time.

        Returns:
            Self: An instance of the class.

        """
        vevents = recurring_ical_events.of(cal, components=[ICalKeys.VEVENT]).between(
            start.datetime, end.datetime
        )

        return cls(
            start=start, end=end, events=[Event.from_ical(vevent) for vevent in vevents]
        )
