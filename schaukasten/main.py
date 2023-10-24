from typing import Annotated

import pendulum
import typer


def main(
    year: Annotated[
        int,
        typer.Argument(
            default_factory=pendulum.now().year,
            help="The year, for which to create the docs. The default is the current year.",
        ),
    ],
    week: Annotated[
        int,
        typer.Argument(
            default_factory=pendulum.now().week_of_year,
            min=1,
            max=52,
            help="The week, for which to create the docs. The default is the current week.",
        ),
    ],
    url: Annotated[
        str,
        typer.Argument(help="The URL where to source calendar is found.", envvar="URL"),
    ],
):
    pass


if __name__ == "__main__":
    typer.run(main)
