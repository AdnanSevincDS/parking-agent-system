from uuid import UUID

from langchain.agents import create_agent
from langchain_core.documents import Document
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

from parking_agent_system.config import settings
from parking_agent_system.data_layer.vector_manager import ParkingVectorStore
from parking_agent_system.services import reservation_flow

from parking_agent_system.tools.parking_info import build_parking_info_tool
from parking_agent_system.tools.reservation import build_reservation_tool

SYSTEM_PROMPT = settings.system_prompt_path.read_text(encoding="utf-8").strip()

class ParkingChatAgent:
    def __init__(self,vector_store: ParkingVectorStore | None = None):
        self._llm = ChatOllama(
            model=settings.ollama_chat_model,
            base_url=settings.ollama_base_url,
            temperature=settings.model_temperature,
        )
        self._vector_store = vector_store or ParkingVectorStore()
        self._last_sources: dict[UUID, list[Document]] = {}

    def _build_tools(self, conversation_id: UUID) -> list:
        return [
            build_parking_info_tool(
                vector_store=self._vector_store,
                last_sources=self._last_sources,
                conversation_id=conversation_id,
            ),
            build_reservation_tool(conversation_id=conversation_id),
        ]

    def run(self, message: str, conversation_id: UUID) -> tuple[str, list[Document]]:
        active = reservation_flow._sessions.get(conversation_id)
        session_context = (
            "You are currently collecting reservation details. "
            "Continue using make_parking_reservation."
            if active else ""
        )
        tools = self._build_tools(conversation_id)
        agent = create_agent(
            model=self._llm,
            tools=tools,
            system_prompt=SYSTEM_PROMPT + ("\n\n" + session_context if session_context else ""),
        )
        result = agent.invoke({"messages": [HumanMessage(content=message)]})
        sources = self._last_sources.pop(conversation_id, [])
        return result["messages"][-1].content, sources