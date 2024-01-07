import re
from enum import StrEnum, auto
from typing import Annotated, Optional, Self

import arrow
import recurring_ical_events
from icalendar import Calendar, Event
from pydantic import AfterValidator, BaseModel, ValidationInfo, field_validator

from schaukasten.types import ArrowType


class LangField(BaseModel):
    de: str
    en: str
    # might need to be optional for cases with interdependent defaults


class Title(LangField):
    @field_validator("de")
    def provide_default_de(cls, de_title):
        return de_title or "Kein Titel"

    @field_validator("en")
    def provide_default(cls, en_title: Optional[str], validation_info: ValidationInfo):
        return en_title or validation_info.data["de"]

    @classmethod
    def from_str(cls: Self, str_inp: str) -> Self:
        """
        Create an instance of the class from a string input. splitting titles on "|" and stripping whitespace.

        Args:
            cls (type): The class type.
            str_inp (str): The str_inp string.

        Returns:
            Self: An instance of the class.

        """
        titles = [title.strip() for title in str_inp.split("|")]

        # set none if titles aren't given and let field validators handle defaults
        return cls(
            de=titles[0] if len(titles) > 0 else None,
            en=titles[1] if len(titles) > 1 else None,
        )


class Description(LangField):
    @field_validator("de")
    def provide_default_de(cls, de_description):
        return de_description or ""

    @field_validator("en")
    def provide_default_en(
        cls, en_description: Optional[str], validation_info: ValidationInfo
    ):
        return en_description or validation_info.data["de"]

    @classmethod
    def from_str(cls: Self, str_inp: str) -> Self:
        """
        Create an instance of the class from a string input. removing html markers from description and splitting on triple repetitions of "-" or "-" to languages.

        Args:
            cls (type): The class type.
            str_inp (str): The str_inp string.

        Returns:
            Self: An instance of the class.

        """
        #
        raw_description_cleaned = re.sub(r"<.*?>", "", str_inp).replace("\xa0", " ")
        descriptions = re.split(r"[-_]{3,}", raw_description_cleaned)
        descriptions = [desc.strip() for desc in descriptions]

        # set none if descriptions aren't given and let field validators handle defaults
        return cls(
            de=descriptions[0] if len(descriptions) > 0 else None,
            en=descriptions[1] if len(descriptions) > 1 else None,
        )


class ICalKeys(StrEnum):
    DTSTART = auto()
    DTEND = auto()
    SUMMARY = auto()
    LOCATION = auto()
    DESCRIPTION = auto()
    VEVENT = auto()


class MultiLangEvent(BaseModel):
    """
    Represents an event with start and end times, title, description, and place. The title and description are dicts with a Language Enum Member as key and the string in that language as value. The place defaults to the Queerreferats Address.
    """

    start: ArrowType
    end: ArrowType
    title: Title
    description: Description
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

        # constructing event
        return cls(
            start=ical_event.get(ICalKeys.DTSTART.name).dt,
            end=ical_event.get(ICalKeys.DTEND.name).dt,
            title=Title.from_str(ical_event[ICalKeys.SUMMARY.name]),
            description=Description.from_str(ical_event[ICalKeys.DESCRIPTION.name]),
            place=ical_event.get(ICalKeys.LOCATION.name),
        )

    # FIXME: some parsing error!


class EventSpan(BaseModel):
    start: ArrowType
    end: ArrowType
    events: Annotated[
        list[MultiLangEvent],
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
        vevents = recurring_ical_events.of(
            cal, components=[ICalKeys.VEVENT.name]
        ).between(start.datetime, end.datetime)

        return cls(
            start=start, end=end, events=[Event.from_ical(vevent) for vevent in vevents]
        )
