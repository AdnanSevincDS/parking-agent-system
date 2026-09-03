from uuid import UUID
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from parking_agent_system.data_layer.sql_manager import ParkingDatabase


def build_approve_reservation_tool():
    db = ParkingDatabase()

    @tool
    def approve_reservation(config: RunnableConfig) -> str:
        """Approves the pending reservation."""
        reservation_id = config["configurable"]["thread_id"]
        updated = db.update_reservation_status(UUID(reservation_id), "approved")
        if updated:
            return f"Reservation {reservation_id} has been approved."
        return f"Reservation {reservation_id} not found."

    return approve_reservation