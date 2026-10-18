"""Registry of profile fields: the only keys that may be stored, each with a validated value type.

Adding a field means adding one entry here; no migration is needed (values are JSONB).
"""

from dataclasses import dataclass
from typing import Annotated, Any, Literal

from pydantic import Field, StringConstraints, TypeAdapter

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
TextList = Annotated[list[ShortText], Field(max_length=20)]

EducationStage = Literal[
    "class_9",
    "class_10",
    "class_11",
    "class_12",
    "iti_or_diploma",
    "undergraduate",
    "graduate",
    "not_in_school",
]
DeviceType = Literal["basic_phone", "smartphone", "shared_device", "computer"]
Connectivity = Literal["good", "patchy", "poor"]


@dataclass(frozen=True)
class FieldSpec:
    key: str
    description: str
    adapter: TypeAdapter[Any]

    def validate(self, value: Any) -> Any:
        """Return the normalised, JSON-safe value or raise pydantic.ValidationError."""
        return self.adapter.dump_python(self.adapter.validate_python(value), mode="json")


def _spec(key: str, description: str, type_: Any) -> FieldSpec:
    return FieldSpec(key, description, TypeAdapter(type_))


_SPECS = [
    _spec("education_stage", "Current education stage", EducationStage),
    _spec("subjects_studied", "Subjects studied", TextList),
    _spec("subject_preferences", "Subjects the student likes", TextList),
    _spec("interests", "Interests and activities", TextList),
    _spec("skills", "Skills", TextList),
    _spec("goals", "Career or education goals", TextList),
    _spec(
        "weekly_learning_hours",
        "Hours per week available for learning",
        Annotated[int, Field(ge=0, le=70, strict=True)],
    ),
    _spec("device_type", "Device used", DeviceType),
    _spec("connectivity", "Internet connection quality", Connectivity),
    _spec(
        "annual_family_income_inr",
        "Family income per year in rupees (asked only for schemes with an income limit)",
        Annotated[int, Field(ge=0, le=100_000_000, strict=True)],
    ),
    _spec("state", "State of residence", ShortText),
    _spec("district", "District of residence", ShortText),
]

FIELDS: dict[str, FieldSpec] = {s.key: s for s in _SPECS}
