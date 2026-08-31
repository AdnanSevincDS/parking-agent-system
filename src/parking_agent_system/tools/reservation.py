import dateparser
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
        Book a parking spot. Collect the user's name, surname, car number (format: AB 1234 CD),
        start datetime, and end datetime through conversation before calling this tool.
        Only call when you have ALL five fields confirmed by the user.
        """
        # Parse the start and end datetime strings into datetime objects
        start = dateparser.parse(reservation_start, settings={"PREFER_DATES_FROM": "future"})
        end = dateparser.parse(reservation_end, settings={"PREFER_DATES_FROM": "future"})

        if not start or not end:
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