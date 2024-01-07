from rich.console import Console
from rich.prompt import Confirm, Prompt

from schaukasten.display import RenderableEventSpan
from schaukasten.types import Language


def print_intro_text(year: int, week: int, langs: Language, url: str):
    console = Console()
    console.rule("[bold]Welcome to the Queerrefs Schaukasten Script![/bold]")
    console.print(
        "This script will help you to create a pdf for the queerreferat schaukasten."
    )
    console.print(
        f"You selected the following options:\n Selected Languages: {', '.join([str(l) for l in langs])}\n year: {year}\n week: {week}\n url: {url} \n\n"
    )
    # TODO: rich columns for this


def confirm_table(events: RenderableEventSpan, lang: Language):
    console = Console()
    events.print_to_terminal(console)

    user_not_yet_confirmed = True
    while user_not_yet_confirmed:
        filter_choice = Prompt.ask(
            "You can now filter the events with a comma separated list [i.e. 1:3,5 excludes events 1, 2, 3 and 5 | Leave empty for all events]:"
        )

        if filter_choice == "":
            return events

        filter_indices = []
        for choice in filter_choice.split(","):
            if ":" in choice:
                start, end = choice.split(":")
                filter_indices.extend(range(int(start), int(end)))
            else:
                filter_indices.append(int(choice))

        new_events = RenderableEventSpan(
            start=events.start,
            end=events.end,
            lang=events.lang,
            events=[
                events.events[i]
                for i in range(len(events.events))
                if i not in filter_indices
            ],
        )
        new_events.print_to_terminal(console)
        user_not_yet_confirmed = Confirm.ask("Are these the events you want to print?")
    return new_events


# def cli_produce_pdf( year: int, week: int, lang: Optional[Language]):
