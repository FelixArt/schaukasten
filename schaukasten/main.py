from operator import call
from typing import Annotated, Optional

import arrow
import typer
from read import read_calendar_from_url, url_is_valid
from rich import print

from schaukasten.display import RenderableEventSpan
from schaukasten.events import EventSpan
from schaukasten.terminal import confirm_table, print_intro_text
from schaukasten.types import Language

from rich.traceback import install

install(show_locals=False)

DEFAULT_URL = "https://calendar.google.com/calendar/ical/queerreferat.aachen%40gmail.com/public/basic.ics"


def url_callback(url: str) -> str:
    if not url_is_valid(url):
        raise typer.BadParameter("The url must be valid.")
    return url


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
    lang: Annotated[
        Optional[Language],
        typer.Option(help="The language to use for rendering."),
    ] = None,
    url: Annotated[
        str,
        typer.Option(
            help="The URL where to source calendar is found.", callback=url_callback
        ),
    ] = DEFAULT_URL,
):
    start = arrow.get((year, week, 1))
    end = start.ceil("week")
    lang = [lang] if lang else list(Language)

    print_intro_text(year, week, lang, url)

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
