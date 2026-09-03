from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

class Intent(str, Enum):
    """Supported user intent categories"""
    INFORMATION = "information"
    RESERVATION = "reservation"
    UNKNOWN = "unknown"

class ConversationStatus(str, Enum):
    """Current status of a chat conversation"""
    ANSWERED = "answered"

class HealthResponse(BaseModel):
    """Safe health-check response for the backend"""
    status: str = Field(default="ok")
    service: str = Field(default="parking_agent_system")
    version: str = Field(default="0.1.0")

class ChatRequest(BaseModel):
    """Validated request received by the chat endpoint"""
    
    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID = Field(description="client-generated ID used to group conversation messages"
    )
    message: str = Field(
        min_length=1,
        max_length=200,
        description="User chat message."
    )
    @field_validator("message")
    @classmethod
    def strip_and_validate_message(cls, value: str) -> str:
        """Trim white space and reject empty messages."""
        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("Message cannot be empty or whitespace only.")
        return cleaned_value
class SourceReference(BaseModel):
    """Safe public source information returned to UI"""

    document_id: str
    title: str

class ChatResponse(BaseModel):
    """Safe response returned by the chat endpoint"""
    conversation_id: UUID
    request_id: UUID = Field(default_factory=uuid4)

    message: str
    intent: Intent
    conversation_status: ConversationStatus

    sources: list[SourceReference] = Field(default_factory=list)

class ReservationStatus(str, Enum):
    """Current status of a reservation request"""
    APPROVED = "approved"
    REFUSED = "refused"

class AdminChatRequest(BaseModel):
    reservation_id: UUID
    message: ReservationStatus

class AdminChatResponse(BaseModel):
    reservation_id: UUID
    message: str

class PendingReservation(BaseModel):
    reservation_id: str
    conversation_id: str
    customer_name: str
    customer_surname: str
    car_number: str
    reservation_start: str
    reservation_end: str
    status: str
    created_at: str

class PendingReservationsResponse(BaseModel):
    reservations: list[PendingReservation]
    total: int