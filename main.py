from parking_agent_system.agents.user_agent import ParkingChatAgent
from parking_agent_system.data_layer.vector_manager import ParkingVectorStore, STATIC_INFO_PATH
from parking_agent_system.services.rag_service import ParkingRAGService


def main() -> None:

    # =====Testing the ParkingChatAgent (chat with ollama)=====
    # agent = ParkingChatAgent()
    # messages = [{
    #     "role": "system", "content": "You are a helpful parking assistant."},
    #     {"role": "user", "content": "What is the parking capacity?"}]
    # response = agent.generate_response(messages)
    # print("Response:", response)

    # =====Testing ParkingVectorStore _parse_static_info_ functionalities (parsing)=====
    # store = ParkingVectorStore()
    # documents = store._parse_static_info(STATIC_INFO_PATH)
    # print("Parsed Documents:", len(documents))
    # for doc in documents[:3]:  
    #     print(doc.metadata, doc.page_content[:100]) 

    # =====Testing the ingestion of static information into Milvus Lite (Saving to vector database)=====
    # store = ParkingVectorStore()
    # print("Starting Milvus Lite ingestion...")
    # chunk_count = store.ingest_static_information()
    # print(f"Ingested chunks: {chunk_count}")
    
    # =====Testing the ingestion of static information into Milvus Lite and searching (Retrieval)=====
    # store = ParkingVectorStore()
    # print("Starting Milvus Lite ingestion...")
    # chunk_count = store.ingest_static_information()
    # print(f"Ingested chunks: {chunk_count}")
    
    # #query = "What are the parking operating hours?"
    # query = "Where is the parking facility located?"
    # result = store.search(query, top_k=3)
    # for idx, doc in enumerate(result, start=1):
    #     print(f"Rank {idx}:")
    #     print("Metadata:", doc.metadata)
    #     print("Document ID:", doc.metadata.get("document_id"))
    #     print("Document title:", doc.metadata.get("title"))
    #     print("Content:", doc.page_content[:200], "...\n")
    
    # == ===Testing the RAG service (Retrieval-Augmented Generation)=====
    #question = "What is the current number of free parking spaces?"
    question = "What are the parking operating hours?"

    rag_service = ParkingRAGService()
    answer, documents = rag_service.answer_question(question, top_k=3)

    print(f"\nQuestion: {question}")
    print(f"\nAnswer:\n{answer}")

    print("\nSources:")
    for document in documents:
        document_id = document.metadata.get("document_id", "unknown")
        title = document.metadata.get("title", "Unknown source")
        print(f"- {document_id} | {title}")


if __name__ == "__main__":
    main()