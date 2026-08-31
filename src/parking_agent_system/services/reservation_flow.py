import dateparser
from uuid import UUID

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from pydantic import BaseModel

from parking_agent_system.api.schemas import ConversationStatus, ReservationField
from parking_agent_system.config import settings
from parking_agent_system.services.reservation_service import ReservationService
from parking_agent_system.services.reservation_validation import (
    validate_car_number,
    validate_name,
)

OPENING_MESSAGE = (
    "To make a reservation please provide: your name, surname, "
    "car number, and start and end date/time. "
    "Example: John Doe, WA 1234 AB, 20-09-2026 10:00 to 20-09-2026 12:00."
)

REQUIRED_FIELDS = [f.value for f in ReservationField]

_sessions: dict[UUID, dict] = {}

class ReservationDetails(BaseModel):
    """Data model for reservation details collected from the user."""
    name: str | None = None
    surname: str | None = None
    car_number: str | None = None
    reservation_start: str | None = None
    reservation_end: str | None = None

def _build_llm_extractor():
    llm = ChatOllama(
        model=settings.ollama_chat_model,
        base_url=settings.ollama_base_url,
        temperature=settings.model_temperature,
    )
    messages = [
        (
        "system",
        "You are a helpful assistant that extracts reservation details from user input. "
        "The required fields are: name, surname, car number, reservation start date/time, "
        "and reservation end date/time."
        ),
        (
            "human", "{message}"
        ),
    ]
    prompt= ChatPromptTemplate.from_messages(messages)

    structured_llm = prompt | llm.with_structured_output(ReservationDetails)
    
    return structured_llm


_extractor = _build_llm_extractor()

def _validate_and_merge(details: ReservationDetails, collected: dict) -> list[str]:
    errors = []
    if details.name:
        try:
            collected["name"] = validate_name(details.name, "Name")
        except ValueError as e:
            errors.append(str(e))
    if details.surname:
        try:
            collected["surname"] = validate_name(details.surname, "Surname")
        except ValueError as e:
            errors.append(str(e))
    if details.car_number:
        try:
            collected["car_number"] = validate_car_number(details.car_number)
        except ValueError as e:
            errors.append(str(e))
    for field in ("reservation_start", "reservation_end"):
        value = getattr(details, field)
        if value:
            parsed = dateparser.parse(value, settings={"PREFER_DATES_FROM": "future"})
            if parsed is None:
                errors.append(
                    f"Could not understand {field.replace('_', ' ')}. "
                    "Use format: 20-09-2026 10:00."
                )
            else:
                collected[field] = parsed

    return errors

def process_turn(
    conversation_id: UUID, 
    message: str,
    reservation_service: ReservationService | None = None
) -> tuple[str, ConversationStatus, ReservationField | None, list[ReservationField]]:
    is_new = conversation_id not in _sessions
    if is_new:
        _sessions[conversation_id] = {
            "collected": {},
        }
    collected = _sessions[conversation_id]["collected"]

    details = _extractor.invoke({"message": message})
    errors = _validate_and_merge(details, collected)

    if is_new and not collected:
        return (
            OPENING_MESSAGE,
            ConversationStatus.COLLECTING_RESERVATION_DETAILS,
            None,
            [],
        )
    
    missing = [f for f in REQUIRED_FIELDS if f not in collected]
    collected_fields = [ReservationField(f) for f in REQUIRED_FIELDS if f in collected]

    if errors or missing:
        parts = []
        if errors:
            parts.append("Errors:\n" + "\n".join(errors))
        if missing:
            parts.append(
                "Missing fields:\n" + "\n".join(f"- {f.replace('_', ' ')}" for f in missing)
            )
        return (
            " ".join(parts),
            ConversationStatus.COLLECTING_RESERVATION_DETAILS,
            None,
            collected_fields,
        )
    
    service = reservation_service or ReservationService()
    result = service.create_pending_reservation(
        conversation_id=conversation_id,
        customer_name=collected["name"],
        customer_surname=collected["surname"],
        car_number=collected["car_number"],
        reservation_start=collected["reservation_start"],
        reservation_end=collected["reservation_end"],
    )
    del _sessions[conversation_id]
    return (
        f"Reservation submitted (ID: {result.reservation_id}). Pending approval.",
        ConversationStatus.RESERVATION_DETAILS_COMPLETED,
        None,
        [ReservationField(f) for f in REQUIRED_FIELDS],
    )