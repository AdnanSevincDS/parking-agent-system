from datetime import datetime, timedelta
from uuid import uuid4

from parking_agent_system.data_layer.sql_manager import (
    PENDING_APPROVAL_STATUS,
    ParkingDatabase,
)

def test_create_and_get_pending_reservation(tmp_path) -> None:
    database = ParkingDatabase(data_base_path=tmp_path / "test_parking.db")
    database.initialize_schema()

    conversation_id = uuid4()
    reservation_start = datetime.now() + timedelta(days=1)
    reservation_end = reservation_start + timedelta(hours=2)

    reservation_id = database.create_pending_reservation(
        conversation_id=conversation_id,
        customer_name="Test",
        customer_surname="Customer",
        car_number="ABC123",
        reservation_start=reservation_start,
        reservation_end=reservation_end,
    )

    reservation = database.get_reservation(reservation_id)
    assert reservation is not None
    assert reservation["reservation_id"] == str(reservation_id)
    assert reservation["conversation_id"] == str(conversation_id)
    assert reservation["customer_name"] == "Test"
    assert reservation["customer_surname"] == "Customer"
    assert reservation["car_number"] == "ABC123"
    assert reservation["reservation_start"] == reservation_start.isoformat()
    assert reservation["reservation_end"] == reservation_end.isoformat()

def test_get_missing_reservation_returns_none(tmp_path) -> None:
    database = ParkingDatabase(data_base_path=tmp_path / "test_parking.db")
    database.initialize_schema()

    reservation = database.get_reservation(uuid4())

    assert reservation is None