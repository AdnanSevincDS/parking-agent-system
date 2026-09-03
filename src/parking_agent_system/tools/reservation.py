from datetime import datetime
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from parking_agent_system.services.reservation_service import ReservationService
from pydantic import BaseModel, Field

class ReservationInput(BaseModel):
    name: str = Field(description="Customer's first name")
    surname: str = Field(description="Customer's last name")
    car_number: str = Field(description="Car number plate, format: AB 1234 CD")
    reservation_start: str = Field(description="Start datetime, e.g. 20-09-2026 10:00")
    reservation_end: str = Field(description="End datetime, e.g. 20-09-2026 12:00")


def build_reservation_tool():
    service = ReservationService()
    
    @tool(args_schema=ReservationInput)
    def make_parking_reservation(
        name: str,
        surname: str,
        car_number: str,
        reservation_start: str,
        reservation_end: str,
        config: RunnableConfig,
    ) -> str:
        """
        Book a parking spot. Only call this tool when the user has submitted the reservation form
        from the sidebar with all five fields: name, surname, car number, start datetime and end datetime.
        Do not collect fields through conversation — direct the user to the sidebar form instead.
        """
        # Parse the start and end datetime strings into datetime objects
        try:
            start = datetime.strptime(reservation_start, "%d-%m-%Y %H:%M")
            end = datetime.strptime(reservation_end, "%d-%m-%Y %H:%M")
        except ValueError:
            return "Could not parse the dates. Please use format: 20-09-2026 10:00."

        try:
            result = service.create_pending_reservation(
                conversation_id=UUID(config["configurable"]["thread_id"]),
                customer_name=name,
                customer_surname=surname,
                car_number=car_number,
                reservation_start=start,
                reservation_end=end,
            )
            return f"Reservation submitted (ID: {result.reservation_id}). Pending approval."
        except Exception as e:
            return f"Validation error: {e}. Please correct and try again."
    return make_parking_reservation