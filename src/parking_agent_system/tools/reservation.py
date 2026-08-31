from uuid import UUID
from langchain_core.tools import tool
from parking_agent_system.services import reservation_flow

def build_reservation_tool(
    conversation_id: UUID
):
    """Create a parking reservation tool for a specific conversation."""
    @tool
    def make_parking_reservation(message: str) -> str:
        """
        Start or continue collecting the details needed to book a parking spot. Pass the user's original message directly to this tool. Use this whenever the user wants to reserve, book, or hold a parking spot.
        """
        response, _, _, _ = reservation_flow.process_turn(conversation_id, message)
        return response
    
    return make_parking_reservation