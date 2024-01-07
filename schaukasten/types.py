from datetime import datetime
from enum import StrEnum, auto
from typing import Annotated

import arrow
from pydantic import PlainSerializer, PlainValidator


class Language(StrEnum):
    de = auto()
    en = auto()


def arrow_constructor(inp: int | float | datetime | str | arrow.Arrow) -> arrow.Arrow:
    """
    Constructs an Arrow object from the given input. KNOWN LIMITATION: the arrow.get function cna take multiple arguments but that cannot be modeled with pydantic. So not all inputs to arrow.get() are allowed here. But a lot of coercion cases are covered.

    Parameters:
        inp (int | float | datetime | str | arrow.Arrow): The input value to construct the Arrow object from.

    Returns:
        arrow.Arrow: The constructed Arrow object.
    """
    return arrow.get(inp)


def arrow_serializer(time: arrow.Arrow) -> str:
    return time.isoformat()


ArrowType = Annotated[
    arrow.Arrow,
    PlainValidator(arrow_constructor),
    PlainSerializer(arrow_serializer),
]
