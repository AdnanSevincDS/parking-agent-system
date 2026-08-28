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

if st.sidebar.button("Clear chat"):
    st.session_state.messages = []
    st.session_state.conversation_id = str(uuid4())
    st.rerun()

st.title("🅿️ Parking Agent System")
st.caption("Ask questions about parking information and reservations.")

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

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

user_message = st.chat_input("Ask a parking question...")

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
        with st.spinner("Checking parking information..."):
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