# Parking Agent System

A RAG-based parking assistant chatbot that answers questions about parking information and handles reservation requests.

---

## Architecture

```
User → Streamlit UI → FastAPI → LangChain Agent (MemorySaver)
                                      ├── get_parking_information → Milvus (static data)
                                      └── make_parking_reservation → SQLite (reservations)

Input  → GuardRails (DeBERTa injection check + Presidio PII scrub)
Output → GuardRails (Presidio PII filter)
```

## Project Structure

```
parking_agent_system/
├── data/
│   ├── parking_static_info.yaml     # Static parking knowledge base
│   └── evaluation_dataset.yaml      # RAG evaluation Q&A pairs
├── frontend/
│   └── app.py                       # Streamlit chat UI
├── reports/
│   └── evaluation_report.html       # Generated evaluation report
├── scripts/
│   ├── setup.py                     # One-time DB + vector store init
│   └── evaluate.py                  # RAG evaluation script
├── src/parking_agent_system/
│   ├── agents/user_agent.py         # LangChain agent with MemorySaver
│   ├── api/                         # FastAPI routes and schemas
│   ├── config.py                    # Environment settings
│   ├── config_rag.py                # RAG tuning parameters
│   ├── data_layer/
│   │   ├── sql_manager.py           # SQLite reservation storage
│   │   └── vector_manager.py        # Milvus vector store
│   ├── guardrails/pii_guard.py      # Input/output safety filters
│   ├── services/
│   │   ├── reservation_service.py   # Reservation business logic
│   │   └── reservation_validation.py
│   ├── telemetry.py                 # Phoenix tracing setup
│   └── tools/
│       ├── parking_info.py          # RAG retrieval tool
│       └── reservation.py           # Reservation booking tool
├── tests/                           # pytest test suite
└── main.py                          # FastAPI app entry point
```

---

## Setup

### Prerequisites
- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- [Ollama](https://ollama.ai) running locally with models pulled:

```bash
ollama pull qwen2.5:7b          # chat model + RAGAS judge
ollama pull nomic-embed-text    # embeddings
```
```

### Installation
```bash
uv sync
```

### One-time initialisation
Creates the SQLite schema and ingests static parking data into Milvus. Run once before starting the server.
```bash
uv run python scripts/setup.py
```

---

## Running

### Start Phoenix (observability)
```bash
uv run python -m phoenix.server.main serve
```
Open `http://localhost:6006` to view traces.

### Start the API server
```bash
uv run uvicorn main:app --reload
```

### Start the frontend
```bash
uv run streamlit run frontend/app.py
```

---

## Evaluation

Runs RAGAS metrics (faithfulness, context precision/recall), Recall@K, Precision@K, Hit Rate@K, and latency across 10 test questions. Generates an Evidently HTML report and sends traces to Phoenix.

`qwen2.5:7b` is used for **both** the agent and the RAGAS judge. It offers strong tool/function calling for the agent and acceptable JSON-format compliance for the judge role at 7B scale. See the *Note on missing (N/A) RAGAS scores* below for the known trade-off.

> **Note:** Milvus Lite allows only one process to hold the database lock at a time. Stop the API server before running evaluation, otherwise you will get a `DataDirLockedError`. If the error still appears after stopping the server, find and kill the stale process:
> ```bash
> lsof data/milvus_parking.db/LOCK
> kill -9 <PID>
> ```

### Note on missing (N/A) RAGAS scores

Some rows in `reports/evaluation_results.csv` show empty values for `faithfulness`
and/or `context_precision`. Two independent causes:

1. **No context retrieved.** When the agent chooses `make_parking_reservation`
   instead of `get_parking_information`, `retrieved_contexts` is empty and
   RAGAS cannot compute `faithfulness`.

2. **Judge LLM JSON parse failures.** Because a single 7B model
   (`qwen2.5:7b`) serves as both agent and judge, judge outputs occasionally
   deviate from the strict JSON schema RAGAS expects — especially for
   `faithfulness` and `context_precision`, which require per-claim /
   per-context verdicts on longer answers. RAGAS silently records `NaN` for
   those (row, metric) pairs. `context_recall` is more robust because it
   only decomposes the short ground-truth answer.

Deterministic retrieval metrics (`Recall@K`, `Precision@K`, `Hit Rate@K`,
`latency_ms`) are unaffected. A larger judge model (e.g. `qwen2.5:14b` or a
hosted API) would reduce cause 2 further.

```bash
uv run python scripts/evaluate.py
```

Report saved to `reports/evaluation_report.html`.

---

## Tests

```bash
uv run pytest tests/
```

---

## RAG Pipeline

```mermaid
graph TD
    A[User Question] --> B[GuardRails: injection check + PII scrub]
    B --> C[LangChain Agent]
    C --> D[Query Rewriter LLM]
    D --> E[Milvus Vector Search]
    E --> F[Retrieved Context]
    F --> C
    C --> G[Qwen2.5 LLM]
    G --> H[GuardRails: PII filter]
    H --> I[Answer]
```

## Data Model

| Data Type | Storage | Examples |
|---|---|---|
| Static | Milvus (vector) | Location, hours, pricing, rules, contact |
| Dynamic | SQLite | Reservation requests, status |

## Guard Rails

- **Input**: DeBERTa-based ML classifier (`ProtectAI/deberta-v3-base-prompt-injection`) detects prompt injection attempts
- **Input**: Presidio scrubs PII (credit cards, SSNs) before reaching the LLM
- **Output**: Presidio anonymizes sensitive entities in responses

## Evaluation Metrics

| Metric | Description |
|---|---|
| Recall@K | What fraction of relevant documents appeared in the top K results? |
| Precision@K | Normalized: `hits / min(K, num_relevant_docs)` — avoids the misleading 1/K floor when a question has only one labeled relevant document |
| Faithfulness | Is the answer grounded in the retrieved context? |
| Context Precision | Are the retrieved contexts relevant to the question? |
| Context Recall | Does the retrieved context cover the ground truth answer? |
| Latency | End-to-end response time per query |

---

## Future Improvements

### Reranking
After the initial vector search, add a cross-encoder reranker (e.g. `cross-encoder/ms-marco-MiniLM-L-6-v2`) to re-score the top-K candidates and promote the most relevant documents before passing context to the LLM. This is especially useful when the embedding model retrieves semantically similar but less precise results.

### Hybrid Search
Combine dense vector search (current) with sparse BM25 keyword search. Hybrid search improves retrieval for queries that contain specific terms (e.g. phone numbers, exact prices) that dense embeddings can underweight.

### Hyperparameter Evaluation
The current evaluation uses fixed values (`chunk_size=500`, `chunk_overlap=50`, `top_k=5`, `temperature=0.0`). A grid-search evaluation across these parameters would show how each affects retrieval and answer quality metrics. Skipped for now because the dataset is small (10 questions) and current results are already strong — worth revisiting with a larger evaluation set.

### Chunking Strategy
The current implementation uses fixed-size chunking (`chunk_size=500`, `chunk_overlap=50`). Alternative strategies worth exploring as the knowledge base grows:
- **Semantic chunking** — splits on meaning boundaries rather than character count, keeping related sentences together
- **Sentence-window chunking** — retrieves individual sentences but passes surrounding context to the LLM for better coherence
- **Auto-merging retrieval** — stores documents at multiple granularities (small chunks for retrieval, larger parent chunks for context) and merges retrieved child chunks back to their parent before passing to the LLM
