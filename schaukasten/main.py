from typing import Annotated

import pendulum as pd
import typer
from read import read_calendar_from_url


def main(
    year: Annotated[
        int,
        typer.Argument(
            default_factory=pd.now().year,
            help="The year, for which to create the docs. The default is the current year.",
        ),
    ],
    week: Annotated[
        int,
        typer.Argument(
            default_factory=pd.now().week_of_year,
            min=1,
            max=52,
            help="The week, for which to create the docs. The default is the current week.",
        ),
    ],
    url: Annotated[
        str,
        typer.Option(
            help="The URL where to source calendar is found.",
            envvar="CALENDAR_URL",
            show_default=False,
        ),
    ] = "",
):
    fetched_calendar = read_calendar_from_url(url)


if __name__ == "__main__":
    typer.run(main)
