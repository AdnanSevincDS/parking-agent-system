from uuid import UUID

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langchain.agents import create_agent

from parking_agent_system.config import settings
from parking_agent_system.data_layer.vector_manager import ParkingVectorStore
from parking_agent_system.tools.parking_info import build_parking_info_tool
from parking_agent_system.tools.reservation import build_reservation_tool
from parking_agent_system.tools.escalate_to_admin import build_escalate_to_admin_tool

USER_SYSTEM_PROMPT = settings.user_system_prompt_path.read_text(encoding="utf-8").strip()

class ParkingChatAgent:
    def __init__(self, vector_store: ParkingVectorStore | None = None):
        self._llm = ChatOllama(
            model=settings.model,
            base_url=settings.ollama_base_url,
            temperature=settings.temperature,
            num_ctx=settings.llm_context_window,
            num_predict=settings.llm_max_output_tokens,
        )
        self._vector_store = vector_store or ParkingVectorStore()
        self._retrieved_docs: dict[str, list[Document]] = {}
        self._memory = MemorySaver()

        tools = [
            build_parking_info_tool(self._vector_store, self._retrieved_docs, self._llm),
            build_reservation_tool(),
            build_escalate_to_admin_tool(),
        ]
        self._agent = create_agent(
            model=self._llm,
            tools=tools,
            checkpointer=self._memory,
            system_prompt=USER_SYSTEM_PROMPT,
        )

    def run(self, message: str, conversation_id: UUID) -> tuple[str, list[Document]]:
        result = self._agent.invoke(
            {"messages" : [HumanMessage(content=message)]},
            config={"configurable": {"thread_id": str(conversation_id)}}
        )
        sources = self._retrieved_docs.pop(str(conversation_id), [])
        return result["messages"][-1].content, sources