from parking_agent_system.agents.user_agent import ParkingChatAgent
from parking_agent_system.data_layer.vector_manager import ParkingVectorStore, STATIC_INFO_PATH
from parking_agent_system.services.rag_service import ParkingRAGService

from fastapi import FastAPI

from parking_agent_system.api.routes_chat import router


app = FastAPI(
    title="Parking Agent System",
    version="0.1.0",
    description="RAG-based parking information and reservation assistant.",
)

app.include_router(router)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    """Return a minimal backend welcome message."""
    return {
        "message": "Parking Agent System backend is running.",
    }