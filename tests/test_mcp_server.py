from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest

import mcp_server.server as server_module
from mcp_server.server import write_confirmed_reservation
from parking_agent_system.data_layer.sql_manager import ParkingDatabase

def test_write_invalid_uuid():
    result = write_confirmed_reservation("invalid-uuid")
    assert "Invalid" in result

@pytest.mark.parametrize("status, should_fail", [
    ("approved", True),
    ("refused", False),
    ("declined", False),
])
def test_write_confirmed_reservation(tmp_path, monkeypatch, status, should_fail):
    db = ParkingDatabase(data_base_path=tmp_path / "test.db")
    db.initialize_schema()

    reservation_id = db.create_pending_reservation(
        conversation_id=uuid4(),
        customer_name="Test",
        customer_surname="User",
        car_number="ABC123",
        reservation_start=datetime.now() + timedelta(days=1),
        reservation_end=datetime.now() + timedelta(days=1, hours=2),
    )

    db.update_reservation_status(reservation_id, status)
    
    output_file = tmp_path / "confirmed_text.txt"
    monkeypatch.setattr(server_module, "ParkingDatabase", lambda: db)
    monkeypatch.setattr(server_module, "OUTPUT_FILE", output_file)

    write_confirmed_reservation(str(reservation_id))

    assert output_file.exists() == should_fail