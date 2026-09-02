from langchain_core.tools import tool
from parking_agent_system.data_layer.sql_manager import ParkingDatabase


def build_approve_reservation_tool():
    db = ParkingDatabase()
    
    @tool
    def approve_reservation(reservation_id: str) -> str:
        """
        Updates the reservation status to 'approved' for the given reservation ID.
        """
        if db.update_reservation_status(reservation_id, "approved"):
            return f"Reservation {reservation_id} has been approved."
        else:
            return f"Reservation {reservation_id} could not be found."
    
    return approve_reservation
