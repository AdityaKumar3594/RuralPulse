import pytest
from pydantic import ValidationError

from app.modules.profile.fields import FIELDS


def test_valid_values_are_normalised():
    assert FIELDS["interests"].validate(["  farming ", "drawing"]) == ["farming", "drawing"]
    assert FIELDS["education_stage"].validate("class_10") == "class_10"
    assert FIELDS["weekly_learning_hours"].validate(6) == 6


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("education_stage", "phd"),
        ("interests", "farming"),  # must be a list
        ("interests", [""]),
        ("interests", ["x"] * 21),
        ("weekly_learning_hours", -1),
        ("weekly_learning_hours", 71),
        ("weekly_learning_hours", "6"),
        ("weekly_learning_hours", True),
        ("connectivity", "excellent"),
    ],
)
def test_invalid_values_are_rejected(key, value):
    with pytest.raises(ValidationError):
        FIELDS[key].validate(value)
