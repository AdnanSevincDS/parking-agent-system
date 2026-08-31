from fastapi import FastAPI
from parking_agent_system.api.routes_chat import router
from parking_agent_system.telemetry import setup_phoenix_telemetry

# 1. Initialize Phoenix/OpenTelemetry before starting the app
setup_phoenix_telemetry()



# 2. Define the FastAPI app
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