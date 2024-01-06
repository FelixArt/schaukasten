from typing import Annotated, Self

import arrow
from jinja2 import Environment, PackageLoader
from options import Language
from pydantic import AfterValidator, BaseModel
from rich import box
from rich.console import Console
from rich.table import Table

from schaukasten.events import EventSpan


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
        """
        Convert an EventSpan object into a Renderable object with all necessary info for printing or other rendering.

        Args:
            cls (type): The class of the Renderable object.
            events (EventSpan): The EventSpan object to convert.
            lang (Language): The language to use for rendering.

        Returns:
            Self: The converted Renderable object.
        """
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

    def print_to_terminal(self: Self, console: Console):
        """
        Prints the events in a tabular format to the terminal.

        Args:
            console (Console): The console object used for printing.

        Returns:
            None
        """
        table = Table(
            title=f"Week {self.start.isocalendar()[1]} (Language = {self.lang.value})",
            box=box.ROUNDED,
        )
        table.add_column("", justify="right")
        table.add_column("Tag", justify="right")
        table.add_column("Startzeit", justify="right")
        table.add_column("Endzeit", justify="right")
        table.add_column("Titel", justify="left")

        for idx, event in enumerate(self.events):
            table.add_row(
                idx,
                event.start.format("dddd, DD.MM"),
                event.start.format("HH:mm"),
                event.end.format("HH:mm"),
                event.title,
            )

        console.print(table)


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
