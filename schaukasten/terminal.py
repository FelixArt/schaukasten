from rich.console import Console
from rich.prompt import Confirm, Prompt

from schaukasten.display import RenderableEventSpan, print_to_terminal
from schaukasten.options import Language

# def print_introtext():
# TODO: implement intro text

def confirm_table(events: RenderableEventSpan, lang: Language):
    console = Console()
    print_to_terminal(events, console)

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
        print_to_terminal(new_events, console)
        user_not_yet_confirmed = Confirm.ask("Are these the events you want to print?")
    return new_events


# def cli_produce_pdf( year: int, week: int, lang: Optional[Language]):
