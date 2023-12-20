from collections import defaultdict
from enum import IntEnum, auto
from pathlib import Path
from typing import Self

from jinja2 import Environment, PackageLoader
from pydantic import BaseModel

from schaukasten.events import EventSpan, Language


class Weekday(IntEnum):
    MONDAY = auto()
    TUESDAY = auto()
    WEDNESDAY = auto()
    THURSDAY = auto()
    FRIDAY = auto()
    SATURDAY = auto()
    SUNDAY = auto()


class RenderableEventInfo(BaseModel):
    title: str
    description: str
    # TODO: colors


class RenderableWeekInfo(BaseModel):
    week: int
    lang: Language
    events: dict[Weekday, list[RenderableEventInfo]]

    @classmethod
    def from_eventspan(cls: Self, events: EventSpan, lang: Language) -> Self:
        if events.start.isocalendar[1] != events.start.isocalendar[1]:
            raise ValueError(
                "Only EventSpans of 1 or less than 1 week can be rendered as WeekInfo!"
            )

        event_dict = defaultdict(list)
        for event in events.events:
            dayofweek = Weekday[event.start.isoweekday()]

            event_dict[dayofweek].append(
                RenderableEventInfo(
                    title=event.title[lang], description=event.description[lang]
                )
            )
        return cls(week=events.start.isocalendar[1], lang=lang, events=event_dict)


def render_html_from_weekinfo(
    weekinfo: RenderableWeekInfo, template_name: str = "table.html.jinja"
):
    template = Environment(
        loader=PackageLoader("schaukasten"), autoescape=True
    ).get_template(template_name)

    return template.render(weekinfo=weekinfo)
    # TODO: return or write to file?


def render_html_as_pdf(path_to_html: Path):
    raise NotImplementedError
    # TODO: implement
