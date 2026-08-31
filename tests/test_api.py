from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document

from main import app
from parking_agent_system.api import routes_chat

class FakeAgent:
    def run(self, message: str, conversation_id: UUID) -> tuple[str, list[Document]]:
        doc = Document(
            page_content="The parking facility operates 24 hours a day.",
            metadata={
                "document_id": "parking-hours",
                "title": "Operating Hours",
            },
        )
        return "The parking facility operates 24 hours a day.", [doc]


client = TestClient(app)

def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "parking_agent_system",
        "version": "0.1.0",
    }

def test_chat_returns_safe_source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(routes_chat, "agent", FakeAgent())

    response = client.post(
        "/chat",
        json={
            "conversation_id": "b45470ef-b252-49f0-99ba-29cc745624c0",
            "message": "What are the parking operating hours?",
        },
    )
    assert response.status_code == 200

    body = response.json()
    assert body["message"] == "The parking facility operates 24 hours a day."
    assert body["intent"] == "information"
    assert body["conversation_status"] == "answered"
    assert body["sources"] == [{"document_id": "parking-hours", "title": "Operating Hours"}]
    assert "pk" not in str(body)

@pytest.mark.parametrize("message", ["", "   ", "\n\t"])
def test_chat_rejects_blank_messages(message: str) -> None:
    response = client.post(
        "/chat",
        json={
            "conversation_id": "b45470ef-b252-49f0-99ba-29cc745624c0",
            "message": message,
        }
    )

    assert response.status_code == 422