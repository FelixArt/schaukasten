from collections import defaultdict

import pytest

from schaukasten.events import Language, language_field


def test_langfieldconstruction():
    arbitrary_string = "adfgagag"
    field = language_field({Language.GERMAN: arbitrary_string})

    assert field[Language.GERMAN] == arbitrary_string
    assert field["german"] == arbitrary_string
    assert field[Language.ENGLISH] == ""
