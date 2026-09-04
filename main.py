from contextlib import asynccontextmanager

from fastapi import FastAPI

from parking_agent_system.agents.admin_agent import build_admin_agent
from parking_agent_system.api import routes_admin
from parking_agent_system.api.routes_admin import router as admin_router
from parking_agent_system.api.routes_chat import router
from parking_agent_system.telemetry import setup_phoenix_telemetry

# 1. Initialize Phoenix/OpenTelemetry before starting the app
setup_phoenix_telemetry()



# 2. Define the FastAPI app

@asynccontextmanager
async def lifespan(app: FastAPI):
    routes_admin.admin_agent = await build_admin_agent()
    yield

app = FastAPI(
    title="Parking Agent System",
    version="0.1.0",
    description="RAG-based parking information and reservation assistant.",
    lifespan=lifespan,
)

app.include_router(router)
app.include_router(admin_router)

@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    """Return a minimal backend welcome message."""
    return {
        "message": "Parking Agent System backend is running.",
    }