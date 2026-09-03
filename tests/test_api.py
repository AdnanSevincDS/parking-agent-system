from uuid import UUID, uuid4
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document

from main import app
from parking_agent_system.api import routes_chat, routes_admin
from parking_agent_system.data_layer.sql_manager import ParkingDatabase

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

class FakeAdminAgent:
    def run(self, message: str, reservation_id: UUID) -> tuple[str, list]:
        return "Reservation approved", []


def test_get_pending_reservation(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    db = ParkingDatabase(data_base_path=tmp_path / "test.db")
    db.initialize_schema()

    reservation_start_time = datetime.now() + timedelta(days=1)
    reservation_end_time = reservation_start_time + timedelta(hours=2)
    db.create_pending_reservation(
        conversation_id=uuid4(),
        customer_name="Test User",
        customer_surname="Test Surname",
        car_number="ABC123",
        reservation_start=reservation_start_time,
        reservation_end=reservation_end_time,
    )

    monkeypatch.setattr(routes_admin, "db", db)

    response = client.get("/admin/reservations")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["reservations"][0]["customer_name"] == "Test User"
    assert body["reservations"][0]["customer_surname"] == "Test Surname"
    assert body["reservations"][0]["status"] == "pending_approval"
    assert body["reservations"][0]["car_number"] == "ABC123"


def test_admin_chat_returns_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(routes_admin, "admin_agent", FakeAdminAgent())

    response = client.post(
        "/admin/chat",
        json={
            "reservation_id": "b45470ef-b252-49f0-99ba-29cc745624c0",
            "message": "approve",
        }
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Reservation approved"
    assert body["reservation_id"] == "b45470ef-b252-49f0-99ba-29cc745624c0"