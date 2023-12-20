from typing import Annotated

import arrow
import typer
from read import read_calendar_from_url
from rich import print

from schaukasten.events import EventSpan


def main(
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
            min=1,
            max=52,
            help="The week, for which to create the docs. The default is the current week.",
        ),
    ],
    url: Annotated[
        str, typer.Option(help="The URL where to source calendar is found.")
    ] = "https://calendar.google.com/calendar/ical/queerreferat.aachen%40gmail.com/public/basic.ics",
):
    span_start = arrow.get((year, week, 1))
    span_end = span_start.ceil("week")

    fetched_ical_calendar = read_calendar_from_url(url)

    events = EventSpan.from_ical(fetched_ical_calendar, span_start, span_end)
    # TODO: check in rich table
    # TODO: render and send to file
    # TODO: proper defaulting and more typer.Options.


if __name__ == "__main__":
    typer.run(main)
