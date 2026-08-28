from fastapi import APIRouter, HTTPException, status

from parking_agent_system.api.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationStatus,
    HealthResponse,
    Intent,
    SourceReference,
)
from parking_agent_system.services.rag_service import ParkingRAGService

router = APIRouter(tags=["system"])

rag_service = ParkingRAGService()

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="check backend health",
)
def health_check() -> HealthResponse:
    """Return a safe confirmation that the backend is running."""
    return HealthResponse()

@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Ask a parking-information question",
)
def chat(request: ChatRequest) -> ChatResponse:
    """
    Answer a parking information question using a RAG (Retrieval-Augmented Generation) approach.
    """
    try:
        answer, documents = rag_service.answer_question(request.message, top_k=3)
    except Exception as error:
        raise HTTPException(
            satatus_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The parking assistant is temporarily unavailable."
        ) from error
    
    sources: list[SourceReference] = []
    seen_document_ids: set[str] = set()

    for document in documents:
        document_id = document.metadata.get("document_id")
        title = document.metadata.get("title")

        if not isinstance(document_id, str) or not isinstance(title, str):
            continue

        # Avoid duplicate citations
        if document_id in seen_document_ids:
            continue

        seen_document_ids.add(document_id)
        sources.append(
            SourceReference(
                document_id=document_id, 
                title=title
                )
        )

        return ChatResponse(
            conversation_id=request.conversation_id,
            message=answer,
            intent=Intent.INFORMATION,
            conversation_status=ConversationStatus.ANSWERED,
            sources=sources
        )
