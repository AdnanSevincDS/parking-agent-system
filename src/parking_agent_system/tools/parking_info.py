from uuid import UUID

from langchain_core.tools import tool
from parking_agent_system.data_layer.vector_manager import ParkingVectorStore

def build_parking_info_tool(
    vector_store: ParkingVectorStore,
    last_sources: dict,
    conversation_id: UUID
):
    """Create a parking-information retrieval tool for a specific conversation."""
    @tool
    def get_parking_information(query: str) -> str:
        """
        Retrieve relevant parking information—including rules, prices, operating hours, and availability—from the parking knowledge base. Use this for any question about parking details.
        """
        docs = vector_store.search(query, top_k=3)
        last_sources[conversation_id] = docs
  
        if not docs:
            return "I do not have that information in the available parking knowledge base."
        context = [f"[{doc.metadata.get('title', 'Unknown')}]\n{doc.page_content}" for doc in docs]
        return "\n\n---\n\n".join(context)
    
    return get_parking_information