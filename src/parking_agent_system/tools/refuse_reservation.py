from uuid import UUID
from langchain_core.tools import tool
from parking_agent_system.config import settings
from parking_agent_system.data_layer.sql_manager import ParkingDatabase


def build_refuse_reservation_tool():
    db = ParkingDatabase()

    @tool
    def refuse_reservation(reservation_id: str) -> str:
        """
        Updates the reservation status to 'refused' for the given reservation ID.
        """
        if db.update_reservation_status(reservation_id, "refused"):
            return f"Reservation {reservation_id} has been refused."
        else:
            return f"Reservation {reservation_id} could not be found."
            
    return refuse_reservation