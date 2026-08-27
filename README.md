
# The RAG Pipeline

```mermaid
graph TD

A[Question] --> B[Milvus Retrieval]
B --> C[Retrieved Context]
C --> D[Qwen]
D --> E[Groundedn Answer]

```