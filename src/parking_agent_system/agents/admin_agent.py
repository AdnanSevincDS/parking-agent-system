from uuid import UUID

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langchain.agents import create_agent

from parking_agent_system.config import settings
from parking_agent_system.config_rag import rag_config
from parking_agent_system.tools.approve_reservation import build_approve_reservation_tool
from parking_agent_system.tools.refuse_reservation import build_refuse_reservation_tool

ADMIN_SYSTEM_PROMPT = settings.admin_system_prompt_path.read_text(encoding="utf-8").strip()

class AdminAgent:
    def __init__(self):
        self._llm = ChatOllama(
            model=settings.model,
            base_url=settings.ollama_base_url,
            temperature=rag_config.temperature,
            num_ctx=settings.llm_context_window,
            num_predict=settings.llm_max_output_tokens,
        )

        self._memory = MemorySaver()

        tools = [
            build_approve_reservation_tool(),
            build_refuse_reservation_tool(),
        ]
        self._agent = create_agent(
            model=self._llm,
            tools=tools,
            checkpointer=self._memory,
            system_prompt=ADMIN_SYSTEM_PROMPT,
        )

    def run(self, message: str, reservation_id: UUID) -> tuple[str, list[Document]]:
        result = self._agent.invoke(
            {"messages" : [HumanMessage(content=message)]},
            config={"configurable": {"thread_id": str(reservation_id)}}
        )
        return result["messages"][-1].content, []