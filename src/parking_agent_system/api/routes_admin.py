import logging
from fastapi import APIRouter, HTTPException, status
from langgraph.types import Command

from parking_agent_system.api.schemas import (
    AdminChatRequest,
    AdminChatResponse,
    PendingReservation,
    PendingReservationsResponse,
)

from parking_agent_system.data_layer.sql_manager import ParkingDatabase
from parking_agent_system.graph.orchestration import api_graph

logger = logging.getLogger(__name__)
router  = APIRouter(prefix="/admin", tags=["admin"])
db = ParkingDatabase()

@router.get("/reservations", response_model=PendingReservationsResponse)
def get_pending_reservations():
    """Returns all reservations that are pending admin approval."""
    rows = db.get_pending_reservations()
    return PendingReservationsResponse(
        reservations=[PendingReservation(**row) for row in rows],
        total=len(rows)
    )


@router.post("/chat", response_model=AdminChatResponse)
def admin_chat(request: AdminChatRequest) -> AdminChatResponse:
    """Admin sends a decision message to Admin Agent regarding a pending reservation."""
    reservation = db.get_reservation(request.reservation_id)
    if not reservation:
        raise HTTPException(
            status_code=404,
            detail="Reservation not found."
        )

    config = {"configurable": {"thread_id": reservation["conversation_id"]}}

    try:
        result = api_graph.invoke(
            Command(resume=request.message.value),
            config=config,
        )
    except Exception as error:
        logger.exception("admin chat handler failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The admin agent is temporarily unavailable. Please try again later.",
        ) from error
    
    message = result["messages"][-1].content
    return AdminChatResponse(
        reservation_id=request.reservation_id,
        message=message,
    )