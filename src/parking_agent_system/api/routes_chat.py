import logging
logger = logging.getLogger(__name__)

from fastapi import APIRouter, HTTPException, status
from parking_agent_system.agents.user_agent import ParkingChatAgent
from parking_agent_system.api.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationStatus,
    HealthResponse,
    Intent,
    SourceReference,
)

router = APIRouter(tags=["system"])
agent = ParkingChatAgent()

@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Health check endpoint to verify the service is running."""
    return HealthResponse()

@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        message, sources = agent.run(request.message, request.conversation_id)
    except Exception as error:
        logger.exception("chat handler failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The parking assistant is temporarily unavailable.",
        ) from error
    
    source_refs: list[SourceReference] = []
    seen: set[str] = set()
    for doc in sources:
        doc_id = doc.metadata.get("document_id")
        title = doc.metadata.get("title")
        if isinstance(doc_id, str) and isinstance(title, str) and doc_id not in seen:
            seen.add(doc_id)
            source_refs.append(SourceReference(document_id=doc_id, title=title))
    
    return ChatResponse(
        conversation_id =request.conversation_id,
        message=message,
        intent=Intent.INFORMATION,
        conversation_status=ConversationStatus.ANSWERED,
        sources=source_refs
    )