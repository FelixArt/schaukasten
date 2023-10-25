from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum, auto

from arrow import Arrow


class Language(StrEnum):
    ENGLISH = auto()
    GERMAN = auto()


def language_field(*args, **kwargs: str) -> defaultdict[Language, str]:
    return defaultdict(str, *args, **kwargs)


@dataclass
class Event:
    start: Arrow
    end: Arrow
    title: defaultdict[Language, str]
    description: defaultdict[Language, str]
