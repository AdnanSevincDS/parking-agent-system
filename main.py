from parking_agent_system.agents.user_agent import ParkingChatAgent
from parking_agent_system.data_layer.vector_manager import ParkingVectorStore, STATIC_INFO_PATH
from parking_agent_system.services.rag_service import ParkingRAGService

#--------------------------------------------------------------------------#  
#     # =====BEN NOTE=====
#--------------------------------------------------------------------------#  
# I Incremenrally checked the functionalities of the Parking Agent System, including the ParkingChatAgent, ParkingVectorStore, and ParkingRAGService. The following tests were conducted:
# 1. ParkingChatAgent: Successfully generated responses to user messages using the Ollama model
# 2. ParkingVectorStore: Parsed static information from a YAML file, ingested it into Milvus Lite, and performed searches to retrieve relevant documents based on user queries.
# 3. ParkingRAGService: Combined the retrieval of relevant documents from the vector store with the generation of responses using the ParkingChatAgent, providing answers to user questions along with source references.   


# if you want to test the functionalities of the Parking Agent System, you can uncomment the relevant sections in the main() function below. Each section corresponds to a specific component of the system, allowing you to test them individually or in combination.

# def main() -> None:
#--------------------------------------------------------------------------#  
#     # =====Testing the ParkingChatAgent (chat with ollama)=====
#--------------------------------------------------------------------------#  
#     # agent = ParkingChatAgent()
#     # messages = [{
#     #     "role": "system", "content": "You are a helpful parking assistant."},
#     #     {"role": "user", "content": "What is the parking capacity?"}]
#     # response = agent.generate_response(messages)
#     # print("Response:", response)

#--------------------------------------------------------------------------#  
#     # =====Testing ParkingVectorStore _parse_static_info_ functionalities (parsing)=====
#--------------------------------------------------------------------------#  

#     # store = ParkingVectorStore()
#     # documents = store._parse_static_info(STATIC_INFO_PATH)
#     # print("Parsed Documents:", len(documents))
#     # for doc in documents[:3]:  
#     #     print(doc.metadata, doc.page_content[:100]) 

#     # =====Testing the ingestion of static information into Milvus Lite (Saving to vector database)=====
#     # store = ParkingVectorStore()
#     # print("Starting Milvus Lite ingestion...")
#     # chunk_count = store.ingest_static_information()
#     # print(f"Ingested chunks: {chunk_count}")
    
##--------------------------------------------------------------------------#  
#     # =====Testing the ingestion of static information into Milvus Lite and searching (Retrieval)=====
#--------------------------------------------------------------------------#  
#     # store = ParkingVectorStore()
#     # print("Starting Milvus Lite ingestion...")
#     # chunk_count = store.ingest_static_information()
#     # print(f"Ingested chunks: {chunk_count}")
    
#     # #query = "What are the parking operating hours?"
#     # query = "Where is the parking facility located?"
#     # result = store.search(query, top_k=3)
#     # for idx, doc in enumerate(result, start=1):
#     #     print(f"Rank {idx}:")
#     #     print("Metadata:", doc.metadata)
#     #     print("Document ID:", doc.metadata.get("document_id"))
#     #     print("Document title:", doc.metadata.get("title"))
#     #     print("Content:", doc.page_content[:200], "...\n")

#--------------------------------------------------------------------------#   
#     # == ===Testing the RAG service (Retrieval-Augmented Generation)=====
#--------------------------------------------------------------------------#  
#     #question = "What is the current number of free parking spaces?"
#     # question = "What are the parking operating hours?"

#     # rag_service = ParkingRAGService()
#     # answer, documents = rag_service.answer_question(question, top_k=3)

#     # print(f"\nQuestion: {question}")
#     # print(f"\nAnswer:\n{answer}")

#     # print("\nSources:")
#     # for document in documents:
#     #     document_id = document.metadata.get("document_id", "unknown")
#     #     title = document.metadata.get("title", "Unknown source")
#     #     print(f"- {document_id} | {title}")

    

#     # In terminal: uv run uvicorn main:app --reload
# if __name__ == "__main__":
#     main()

#------------------------------------------------#
# =====FastAPI Health Check Endpoint Testing=====
#------------------------------------------------#
from fastapi import FastAPI

from parking_agent_system.api.routes_chat import router


app = FastAPI(
    title="Parking Agent System",
    version="0.1.0",
    description="RAG-based parking information and reservation assistant.",
)

app.include_router(router)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    """Return a minimal backend welcome message."""
    return {
        "message": "Parking Agent System backend is running.",
    }

######## In terminal: uv run uvicorn main:app --reload
# curl -X POST http://127.0.0.1:8000/chat \
#   -H "Content-Type: application/json" \
#   -d '{
#     "conversation_id": "b45470ef-b252-49f0-99ba-29cc745624c0",
#     "message": "What are the parking operating hours?"
#   }'

#######test validation in terminal
# curl -X POST http://127.0.0.1:8000/chat \
#   -H "Content-Type: application/json" \
#   -d '{
#     "conversation_id": "b45470ef-b252-49f0-99ba-29cc745624c0",
#     "message": "    "
#   }'

# >>> {"detail":[{"type":"value_error","loc":["body","message"],"msg":"Value error, Message cannot be empty or whitespace only.","input":"    ","ctx":{"error":{}}}]}%