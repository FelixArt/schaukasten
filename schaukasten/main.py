from dataclasses import dataclass
from typing import Annotated, Optional

import arrow
import typer
from read import read_calendar_from_url
from rich import print

from schaukasten.display import RenderableEventSpan
from schaukasten.events import EventSpan
from schaukasten.options import Language
from schaukasten.terminal import confirm_table


@dataclass
class common_options:
    url: Annotated[
        str,
        typer.Option(
            help="The URL where to source calendar is found.",
            default="https://calendar.google.com/calendar/ical/queerreferat.aachen%40gmail.com/public/basic.ics",
        ),
    ]
    lang: Annotated[
        Optional[Language],
        typer.Option(help="The language to use for rendering.", default=None),
    ]


app = typer.Typer()


@app.command()
def pdf(
    year: Annotated[
        int,
        typer.Argument(
            default_factory=arrow.now().year,
            help="The year, for which to create the docs. The default is the current year.",
        ),
    ],
    week: Annotated[
        int,
        typer.Argument(
            default_factory=arrow.now().week,
            min=0,
            max=52,
            help="The week, for which to create the docs. The default is the current week.",
        ),
    ],
    url: common_options.url,
    lang: common_options.lang,
):
    start = arrow.get((year, week, 1))
    end = start.ceil("week")
    lang = [lang] if lang else list(Language)

    fetched_ical_calendar = read_calendar_from_url(url)
    events = EventSpan.from_ical(fetched_ical_calendar, start, end)

    for lang_opt in lang:
        renderable_events = RenderableEventSpan.from_eventspan(events, lang_opt)
        renderable_events = confirm_table(renderable_events, lang_opt)
        # produce_pdf(renderable_events, lang_opt)


@app.command()
def server():
    raise NotImplementedError


# TODO: render and send to file
# TODO: proper defaulting and more typer.Options.


if __name__ == "__main__":
    app()
