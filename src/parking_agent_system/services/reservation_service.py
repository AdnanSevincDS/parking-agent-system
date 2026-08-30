"""Service for creating validated pending parking reservations."""
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from parking_agent_system.data_layer.sql_manager import (
    PENDING_APPROVAL_STATUS,
    ParkingDatabase,
)
from parking_agent_system.services.reservation_validation import (
    validate_car_number,
    validate_name,
    validate_reservation_period,
)

@dataclass(frozen=True)
class ReservationCreationResult:
    """Safe result returned after a reservation request is created."""
    reservation_id: UUID
    status: str

class ReservationService:
    """Validate and create pending parking reservations."""

    def __init__(self, database: ParkingDatabase | None = None) -> None:
        self._database = database or ParkingDatabase()

    def create_pending_reservation(
        self,
        *,
        conversation_id: UUID,
        customer_name: str,
        customer_surname: str,
        car_number: str,
        reservation_start: datetime,
        reservation_end: datetime,
    ) -> ReservationCreationResult:
        """Validate reservation details and store a pending approval request"""
        validated_name = validate_name(customer_name, "Name")
        validated_surname = validate_name(customer_surname, "Surname")
        validated_car_number = validate_car_number(car_number)

        validated_start, validated_end = validate_reservation_period(
            reservation_start, reservation_end
        )

        reservation_id = self._database.create_pending_reservation(
            conversation_id=conversation_id,
            customer_name=validated_name,
            customer_surname=validated_surname,
            car_number=validated_car_number,
            reservation_start=validated_start,
            reservation_end=validated_end,
        
        )

        return ReservationCreationResult(
            reservation_id=reservation_id,
            status=PENDING_APPROVAL_STATUS,
        )