from pathlib import Path
import yaml

from langchain_core.documents import Document
from langchain_milvus import Milvus
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from parking_agent_system.config import DATA_DIR, settings

COLLECTION_NAME = "parking_static_info"
STATIC_INFO_PATH = DATA_DIR / "parking_static_info.yaml"

PUBLIC_STATIC_CLASSIFICATION = "public_static"


class ParkingVectorStore:
    """Manages public static parking knowledge in a Milvus Lite."""

    def __init__(self,
        chunk_size: int = settings.chunk_size,
        chunk_overlap: int = settings.chunk_overlap,
        top_k: int = settings.top_k
    ):
        self._embeddings = OllamaEmbeddings(
            model=settings.embedding_model,
            base_url=settings.ollama_base_url,
        )
        self._text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def _parse_static_info(self, source_path: Path) -> list[Document]:
        """
        Parse public static-info sections into LangChain Documents.

        Args:
            source_path (Path): Path to the static info text file.
        Returns:
            list[Document]: List of LangChain Document objects.
        """
        if not source_path.exists():
            raise FileNotFoundError(f"Static info file not found: {source_path}")
        
        documents: list[Document] = []
        with open(source_path, "r") as file:
            data = yaml.safe_load(file)

        for item in data:
            metadata = {
                "document_id": item['document_id'], 
                "title": item['title'],
                "data_classification": item["data_classification"],
                "source_file": source_path.name,
            }

            documents.append(
                Document(
                    page_content=item['body'],
                    metadata=metadata
                )
            )
        return documents

    def _create_vector_store(self, *, drop_old: bool = False) -> Milvus:
        """
       Create a Milvus Lite-backed LangChain vector store.

        `drop_old=True` is acceptable for a controlled local rebuild command.
        Never use it in the future chat request path.
        """
        return Milvus(
            embedding_function=self._embeddings,
            collection_name=COLLECTION_NAME,
            connection_args={
                "uri": str(settings.milvus_db_path),
            },
            drop_old=drop_old
        )
    
    def ingest_static_information(self) -> int:
        """
        Rebuild the Milvus collection from approved public static knowledge.

        This method is intended for manual execution or a controlled
        initialization/administrative workflow.

        It must never be called from a user chat request because it drops and
        recreates the development collection.

        Returns:
            The number of chunks successfully ingested.

        Raises:
            ValueError: If the source data is malformed or produces no chunks.
       """
        documents = self._parse_static_info(STATIC_INFO_PATH)
        if not documents:
            raise ValueError("No documents found to ingest.")

        chunks = self._text_splitter.split_documents(documents)
        if not chunks:
            raise ValueError("No chunks created from documents.")

        # Recreate the collection for an explicit local rebuild.
        vector_store = self._create_vector_store(drop_old=True)
        vector_store.add_documents(chunks)

        return len(chunks)

    def search(self, query: str, top_k: int) -> list[Document]:
        """
        Search the Milvus vector store for relevant documents.

        Args:
            query (str): The search query.
            top_k (int): Number of top results to return.
        Returns:
            list[Document]: List of relevant LangChain Document objects.
        """
        
        if not isinstance(query, str):
            raise TypeError("Query must be a string.")
        
        cleaned_query = query.strip()
        
        if not cleaned_query:
            raise ValueError("Query cannot be empty.")
        

        vector_store = self._create_vector_store(drop_old=False)
        results = vector_store.similarity_search(cleaned_query, k=top_k)
        return [
            document
            for document in results
            if document.metadata.get("data_classification") == PUBLIC_STATIC_CLASSIFICATION
        ]