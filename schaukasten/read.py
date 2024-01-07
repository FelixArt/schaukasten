from urllib.parse import urlparse

import requests
from icalendar import Calendar
from rich.console import Console


def url_is_valid(x: str) -> bool:
    """
    url validator taken from https://stackoverflow.com/questions/7160737/how-to-validate-a-url-in-python-malformed-or-not
    """
    try:
        result = urlparse(x)
        return all([result.scheme, result.netloc])
    except:
        return False


def read_calendar_from_url(url: str) -> Calendar:
    """
    Reads a calendar from a url that must be provided.
    """
    console = Console()
    console.log(f"Downloading calendar from {url}...")

    if not url or not url_is_valid(url):
        raise ValueError(f"{url} is not a valid URL.")

    response = requests.get(url)
    if response.status_code != 200:
        raise RuntimeError(
            f"The request to the url {url} returned status code {response.status_code}"
        )
    console.log(f"Successfully downloaded calendar.")

    return Calendar.from_ical(response.text)
