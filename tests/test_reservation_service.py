from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from parking_agent_system.data_layer.sql_manager import (
    PENDING_APPROVAL_STATUS,
    ParkingDatabase,
)
from parking_agent_system.services.reservation_service import ReservationService

def test_create_pending_reservation_validates_and_persists_data(tmp_path) -> None:
    database = ParkingDatabase(data_base_path=tmp_path / "test_parking.db")
    database.initialize_schema()

    service = ReservationService(database=database)

    conversation_id = uuid4()
    reservation_start = datetime.now() + timedelta(days=1)
    reservation_end = reservation_start + timedelta(hours=2)

    result = service.create_pending_reservation(
        conversation_id=conversation_id,
        customer_name=" adnan ",
        customer_surname="sevinc",
        car_number="wa 1234 gb",
        reservation_start=reservation_start,
        reservation_end=reservation_end,
    )

    assert result.status == PENDING_APPROVAL_STATUS

    stored_reservation = database.get_reservation(result.reservation_id)

    assert stored_reservation is not None
    assert stored_reservation["reservation_id"] == str(result.reservation_id)
    assert stored_reservation["conversation_id"] == str(conversation_id)

    # Confirm validation happened before storing
    assert stored_reservation["customer_name"] == "ADNAN"
    assert stored_reservation["customer_surname"] == "SEVINC"
    assert stored_reservation["car_number"] == "WA1234GB"

    assert stored_reservation["reservation_start"] == reservation_start.isoformat()
    assert stored_reservation["reservation_end"] == reservation_end.isoformat()
    assert stored_reservation["status"] == PENDING_APPROVAL_STATUS


def test_create_pending_reservation_rejects_invalid_car_number(tmp_path) -> None:
    database = ParkingDatabase(data_base_path=tmp_path / "test_parking.db")
    database.initialize_schema()

    service = ReservationService(database=database)

    reservation_start = datetime.now() + timedelta(days=1)
    reservation_end = reservation_start + timedelta(hours=2)

    with pytest.raises(ValueError, match="Car number"):
        service.create_pending_reservation(
            conversation_id=uuid4(),
            customer_name="Adnan",
            customer_surname="Sevinc",
            car_number="WA-1234",
            reservation_start=reservation_start,
            reservation_end=reservation_end,
        )