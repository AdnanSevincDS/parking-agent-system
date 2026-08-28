from datetime import datetime, timedelta
from uuid import uuid4

from parking_agent_system.data_layer.sql_manager import ParkingDatabase

def main() -> None:
    database = ParkingDatabase()
    database.initialize_schema()

    reservation_start = datetime.now().astimezone() + timedelta(days=1)
    reservation_end = reservation_start + timedelta(hours=2)

    reservation_id = database.create_pending_reservation(
        conversation_id=uuid4(),
        customer_name="Test",
        customer_surname="User",
        car_number="ABC123",
        reservation_start=reservation_start,
        reservation_end=reservation_end,
    )

    reservation = database.get_reservation(reservation_id)

    print(f"Created reservation ID: {reservation_id}")

    if reservation is not None:
        print(f"Status: {reservation['status']}")
        print(f"Car number: {reservation['car_number']}")
        print(f"Start: {reservation['reservation_start']}")
        print(f"End: {reservation['reservation_end']}")


if __name__ == "__main__":
    main()
