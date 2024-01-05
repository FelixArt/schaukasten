from enum import IntEnum, StrEnum, auto
from pathlib import Path
from typing import Annotated, Self

import arrow
from jinja2 import Environment, PackageLoader
from pydantic import AfterValidator, BaseModel
from rich.table import Table

from schaukasten.events import EventSpan


class Language(StrEnum):
    DE = auto()
    EN = auto()


class Weekday(IntEnum):
    MONDAY = auto()
    TUESDAY = auto()
    WEDNESDAY = auto()
    THURSDAY = auto()
    FRIDAY = auto()
    SATURDAY = auto()
    SUNDAY = auto()


class RenderableEvent(BaseModel):
    title: str
    description: str
    start: arrow.Arrow
    end: arrow.Arrow
    place: str
    # TODO: colors


class RenderableEventSpan(BaseModel):
    start: arrow.Arrow
    end: arrow.Arrow
    lang: Language
    events: Annotated[
        list[RenderableEvent],
        AfterValidator(lambda events: list(sorted(events, key=lambda e: e.start))),
    ]

    @classmethod
    def from_eventspan(cls: Self, events: EventSpan, lang: Language) -> Self:
        events = [
            RenderableEvent(
                title=event.title.model_dump()[lang],
                description=event.description.model_dump()[lang],
                start=event.start,
                end=event.end,
                place=event.place,
            )
            for event in events.events
        ]
        return cls(start=events.start, lang=lang, events=events, end=events.end)


# def render_html_from_weekinfo(
#     weekinfo: RenderableEvent, template_name: str = "table.html.jinja"
# ):
#     template = Environment(
#         loader=PackageLoader("schaukasten"), autoescape=True
#     ).get_template(template_name)

#     return template.render(weekinfo=weekinfo)
#     # TODO: return or write to file?


# def render_html_as_pdf(path_to_html: Path):
#     raise NotImplementedError
#     # TODO: implement


def render_in_terminal(
    weekinfo: RenderableEventSpan, template_name: str = "table.html.jinja"
):
    table = Table(title=f"Week {weekinfo.start.isocalendar()[1]} (Langugage = {weekinfo.lang.value})")
    table.add_column("Tag", justify="right")
    table.add_column("Startzeit", justify="right")
    table.add_column("Endzeit", justify="right")
    table.add_column("Titel", justify="left")

    for day, events in weekinfo.events.items():
        for event in events:
            pass
