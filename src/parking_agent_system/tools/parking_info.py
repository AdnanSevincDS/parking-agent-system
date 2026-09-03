from uuid import UUID

from langchain_core.runnables import RunnableConfig
from langchain_core.runnables import chain as lc_chain
from langchain_core.tools import tool
from parking_agent_system.data_layer.vector_manager import ParkingVectorStore
from parking_agent_system.config import settings
from parking_agent_system.config_rag import rag_config


def build_parking_info_tool(vector_store: ParkingVectorStore, retrieved_docs: dict, llm):
    @lc_chain
    def _rewrite(query: str) -> str:
        return llm.invoke(
            f"Rewrite this into a detailed search query for a parking facility knowledge base. "
            f"Return only the rewritten query, nothing else.\nUser query: {query}"
        ).content
    @tool
    def get_parking_information(query: str, config: RunnableConfig) -> str:
        """
        Retrieve relevant parking information—including rules, prices, operating hours, and availability—from the parking knowledge base. Use this for any question about parking details.
        """
        thread_id  = config["configurable"]["thread_id"]
        docs = vector_store.search(_rewrite.invoke(query), top_k=rag_config.top_k)
        retrieved_docs[thread_id] = docs
  
        if not docs:
            return "I do not have that information in the available parking knowledge base."
        context = [f"[{doc.metadata.get('title', 'Unknown')}]\n{doc.page_content}" for doc in docs]
        return "\n\n---\n\n".join(context)
    
    return get_parking_information