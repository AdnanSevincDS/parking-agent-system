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
    COLLECTING_RESERVATION_DETAILS = "collecting_reservation_details"
    RESERVATION_DETAILS_COMPLETED = "reservation_details_completed"
    BLOCKED = "blocked"
    ERROR = "error"

class ReservationField(str, Enum):
    """"Reservation details that may be collected from the user"""
    NAME = "name"
    SURNAME = "surname"
    CAR_NUMBER = "car_number"
    RESERVATION_START = "reservation_start"
    RESERVATION_END = "reservation_end"

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

    next_required_field: ReservationField | None = None

    collected_fields: list[ReservationField] = Field(default_factory=list)
    sources: list[SourceReference] = Field(default_factory=list)