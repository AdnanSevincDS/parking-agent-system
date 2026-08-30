from datetime import datetime, timedelta, timezone

import pytest

from parking_agent_system.services.reservation_validation import (
    validate_car_number,
    validate_name,
    validate_reservation_period,
)

def test_validate_name_normalizes_to_uppercase() -> None:
    """Test that validate_name normalizes the name to uppercase."""
    assert validate_name("John Doe", "Name") == "JOHN DOE"
    assert validate_name("  Alice  ", "Name") == "ALICE"
    assert validate_name("O'Connor", "Name") == "O'CONNOR"
    assert validate_name("Mary-Jane", "Name") == "MARY-JANE"

@pytest.mark.parametrize(
    "value",
    ["", "   ", "A", "Anna123", "Anna@Smith", "!!!"],
)

def test_validate_name_rejects_invalid_values(value: str) -> None:
    """Test that validate_name rejects invalid names."""
    with pytest.raises(ValueError):
        validate_name(value, "Name")

def test_validate_car_number_normalizes_case_and_spaces() -> None:
    """Test that validate_car_number normalizes the car number."""
    assert validate_car_number(" wa 1234 ab ") == "WA1234AB"
    assert validate_car_number("kr 12345") == "KR12345"


@pytest.mark.parametrize(
    "value",
    ["", "   ", "ABC", "WA-1234", "WA!1234", "WA 12@34", "12345678901"],
)
def test_validate_car_number_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError):
        validate_car_number(value)

def test_validate_reservation_period_accepts_future_period() -> None:
    """Test that validate_reservation_period accepts a valid future period."""
    reservation_start = datetime.now(timezone.utc) + timedelta(days=1)
    reservation_end = reservation_start + timedelta(hours=2)

    result_start, result_end = validate_reservation_period(
        reservation_start, reservation_end
    )
    assert result_start == reservation_start
    assert result_end == reservation_end

def test_validate_reservation_period_rejects_past_start() -> None:
    """Test that validate_reservation_period rejects a past start time."""
    reservation_start = datetime.now(timezone.utc) - timedelta(days=1)
    reservation_end = datetime.now(timezone.utc) + timedelta(hours=1)

    with pytest.raises(ValueError):
        validate_reservation_period(reservation_start, reservation_end)

def test_validate_reservation_period_rejects_end_before_start() -> None:
    """Test that validate_reservation_period rejects an end time before start."""
    reservation_start = datetime.now(timezone.utc) + timedelta(days=1)
    reservation_end = reservation_start - timedelta(hours=1)

    with pytest.raises(ValueError):
        validate_reservation_period(reservation_start, reservation_end)