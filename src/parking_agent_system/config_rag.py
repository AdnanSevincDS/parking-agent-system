from dataclasses import dataclass

from dataclasses import dataclass

@dataclass
class RAGConfig:
    embedding_model: str = "nomic-embed-text:latest"
    temperature: float = 0.0
    top_k: int = 3
    chunk_size: int = 500
    chunk_overlap: int = 50

rag_config = RAGConfig()