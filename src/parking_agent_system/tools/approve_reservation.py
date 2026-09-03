from uuid import UUID
from langchain_core.tools import tool
from parking_agent_system.data_layer.sql_manager import ParkingDatabase


def build_approve_reservation_tool():
    db = ParkingDatabase()
    
    @tool
    def approve_reservation(reservation_id: str) -> str:
        """
        Updates the reservation status to 'approved' for the given reservation ID.
        """
        updated = db.update_reservation_status(UUID(reservation_id), "approved")
        if updated:
            return f"Reservation {reservation_id} has been approved."
        else:
            return f"Reservation {reservation_id} not found."
    
    return approve_reservation