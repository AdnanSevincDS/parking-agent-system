"""Validation helpers for parking reservation details."""

import re
from datetime import datetime


NAME_PATTERN = re.compile(r"^[A-Za-z]+(?:[' -][A-Za-z]+)*$")
CAR_NUMBER_PATTERN = re.compile(r"^[A-Z0-9]{4,10}$")


def validate_name(value: str, field_name: str) -> str:
    """Validate and normalize a customer name or surname."""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string.")

    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")

    cleaned_value = " ".join(value.strip().split())

    if not 2 <= len(cleaned_value) <= 50:
        raise ValueError(
            f"{field_name} must contain between 2 and 50 characters."
        )

    if not NAME_PATTERN.fullmatch(cleaned_value):
        raise ValueError(
            f"{field_name} must contain only English letters, spaces, "
            "hyphens, or apostrophes."
        )

    return cleaned_value.upper()


def validate_car_number(value: str) -> str:
    """Validate and normalize a vehicle registration number."""
    if not isinstance(value, str):
        raise ValueError("Car number must be a string.")

    if not value.strip():
        raise ValueError("Car number cannot be empty.")

    cleaned_value = "".join(value.upper().split())

    if not CAR_NUMBER_PATTERN.fullmatch(cleaned_value):
        raise ValueError(
            "Car number must contain 4-10 letters or digits. "
            "Spaces are allowed, but punctuation is not."
        )

    return cleaned_value


def validate_reservation_period(
    reservation_start: datetime,
    reservation_end: datetime,
) -> tuple[datetime, datetime]:
    """Validate a future reservation period using local parking time."""
    if reservation_start.date() < datetime.now().date():
        raise ValueError("Reservation start time must be in the future.")

    if reservation_end <= reservation_start:
        raise ValueError("Reservation end time must be after the start time.")

    return reservation_start, reservation_end