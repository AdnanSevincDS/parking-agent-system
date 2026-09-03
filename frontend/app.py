from datetime import date, time
import os
from uuid import uuid4

import httpx
import streamlit as st

API_BASE_URL = os.getenv("PARKING_API_BASE_URL", "http://localhost:8000")
CHAT_ENDPOINT = f"{API_BASE_URL}/chat"


st.set_page_config(
    page_title="Parking Agent System",
    page_icon="🅿️",
    layout="centered",
)

st.title("🅿️ Parking Agent System")
st.caption("Ask questions about parking information and reservations.")

# Placed directly in the main layout
if st.button("Clear chat", type="secondary"):
    st.session_state.messages = []
    st.session_state.conversation_id = str(uuid4())
    st.rerun()

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_date_message" not in st.session_state:
    st.session_state.pending_date_message = None

with st.sidebar:
    st.subheader("📅 Make a Reservation")
    st.caption("Fill in your details and click 'Send to chat' to submit your reservation request.")

    res_name = st.text_input("First name")
    res_surname = st.text_input("Surname")
    res_car = st.text_input("Car number plate", placeholder="e.g. WA 1234 AB")
    start_date = st.date_input("Start date", min_value=date.today())
    start_time = st.time_input("Start time", value=time(10, 0))
    end_date = st.date_input("End date", min_value=date.today())
    end_time = st.time_input("End time", value=time(12, 0))

    if st.button("Send to chat", type="primary"):
        if not res_name or not res_surname or not res_car:
            st.warning("Please fill in all fields.")
        else:
            formatted_start = f"{start_date.strftime('%d-%m-%Y')} {start_time.strftime('%H:%M')}"
            formatted_end = f"{end_date.strftime('%d-%m-%Y')} {end_time.strftime('%H:%M')}"
            st.session_state.pending_date_message = (
                f"Name: {res_name} | "
                f"Surname: {res_surname} | "
                f"Car: {res_car} | "
                f"Reservation: {formatted_start} to {formatted_end}"
            )
            st.rerun()

def display_sources(sources: list[dict]) -> None:
    """Render safe public source references in the Streamlit app."""
    if not sources:
        return

    with st.expander("Sources", expanded=False):
        for source in sources:
            document_id = source.get("document_id", "unknown")
            title = source.get("title", "Unknown source")
            st.write(f"- **{title}** (`{document_id}`)")

for chat_message in st.session_state.messages:
    with st.chat_message(chat_message["role"]):
        st.markdown(chat_message["content"])

        if chat_message["role"] == "assistant":
            display_sources(chat_message.get("sources", []))

chat_input = st.chat_input("Ask a parking question...")

pending = st.session_state.pending_date_message
if pending:
    st.session_state.pending_date_message = None

user_message = pending or chat_input

if user_message:
    user_message = user_message.strip()

    if not user_message:
        st.warning("Please enter a non-empty message.")
        st.stop()
    
    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_message,
        }
    )

    with st.chat_message("user"):
            st.markdown(user_message)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = httpx.post(
                    CHAT_ENDPOINT,
                    json={
                        "conversation_id": st.session_state.conversation_id,
                        "message": user_message,
                    },
                    timeout=60.0,
                )
                response.raise_for_status()
                
                response_data = response.json()
                answer = response_data["message"]
                sources = response_data.get("sources", [])

                st.markdown(answer)
                display_sources(sources)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                    }
                )
            except httpx.HTTPStatusError:
                st.error(
                    "The parking assistant could not process that request. "
                    "Please check your message and try again."
                )
            except httpx.RequestError:
                st.error(
                    "The backend is unavailable. Make sure FastAPI is running "
                    "at http://127.0.0.1:8000."
                )
            except (KeyError, ValueError):
                st.error(
                    "The backend returned an unexpected response. "
                    "Please try again later."
                )