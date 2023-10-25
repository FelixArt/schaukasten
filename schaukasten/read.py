from urllib.parse import urlparse

import requests
from icalendar import Calendar


def url_is_valid(x: str) -> bool:
    """
    url validator taken from https://stackoverflow.com/questions/7160737/how-to-validate-a-url-in-python-malformed-or-not
    """
    try:
        result = urlparse(x)
        return all([result.scheme, result.netloc])
    except:
        return False


def read_calendar_from_url(url: str):
    """
    Reads a calendar from a url that must be provided.
    """

    if not url or not url_is_valid(url):
        raise ValueError(f"{url} is not a valid URL.")

    response = requests.get(url)
    if response.status_code != 200:
        raise RuntimeError(
            f"The request to the url {url} returned status code {response.status_code}"
        )

    calendar = Calendar.from_ical(response.text)
    return
