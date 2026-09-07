# Parking Agent System

A RAG-based parking assistant chatbot that answers questions about parking information, handles reservation requests, and routes them to a human administrator for approval.

---

## Submission Guide for Assessors

This project is built incrementally across stages. Errors and logic were refined progressively — some fixes introduced in a later stage also improved earlier stage code. For the corrected and complete code across all stages, please refer to the **`main` branch**.

---

## Architecture

```
User → Streamlit UI → FastAPI → LangGraph orchestration (SqliteSaver)
                                    ├── user_interaction node
                                    │       └── ParkingChatAgent (MemorySaver)
                                    │               ├── get_parking_information → Milvus (static data)
                                    │               ├── make_parking_reservation → SQLite (pending_approval)
                                    │               └── escalate_to_admin → queues for human review
                                    │
                                    ├── wait_for_admin node  ← INTERRUPT (human-in-the-loop)
                                    │
                                    ├── admin_approval node
                                    │       ├── approve_reservation → SQLite (approved)
                                    │       └── refuse_reservation  → SQLite (refused)
                                    │
                                    └── write_confirmation node
                                            └── MCP Server (port 8001)
                                                    └── confirmed_reservations.txt

Admin → GET /admin/reservations → list all pending reservations

Input  → GuardRails (DeBERTa injection check + Presidio PII scrub)
Output → GuardRails (Presidio PII filter)
```

## End-to-End Flow

```
STARTUP
───────
MCP server starts on port 8001 (separate process)
FastAPI starts — api_graph (LangGraph + SqliteSaver) is ready at module load


USER FLOW
─────────
User fills sidebar form → Streamlit sends POST /chat
  → LangGraph runs user_interaction node
      → ParkingChatAgent calls make_parking_reservation tool
          → saves to SQLite (status: pending_approval)
      → ParkingChatAgent calls escalate_to_admin
      → graph checks SQLite: reservation found for this conversation_id
      → graph routes to wait_for_admin node → INTERRUPT (state persisted in SqliteSaver)
  → User sees: "Your reservation is pending admin approval"


ADMIN FLOW
──────────
Admin sends GET /admin/reservations
  → sees all pending reservations with their UUIDs

Admin picks one, sends POST /admin/chat
  {"reservation_id": "uuid-A", "message": "approved"}

  → routes_admin.py looks up conversation_id from reservation_id in SQLite
  → resumes graph via Command(resume="approved"), thread_id = conversation_id

  IF approved:
    → admin_approval node calls approve_reservation tool
        → updates SQLite status to "approved"
    → graph routes to write_confirmation node
        → calls MCP server write_confirmed_reservation(uuid-A)
            → MCP server queries SQLite for full details
            → appends to data/confirmed_reservations.txt:
              "John Smith | WA 1234 AB | 04-09-2026 10:00 to 04-09-2026 12:00 | 04-09-2026 14:35"

  IF refused:
    → admin_approval node calls refuse_reservation tool
        → updates SQLite status to "refused"
    → graph routes to END (write_confirmation is skipped)
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
│   ├── agents/
│   │   ├── user_agent.py            # Agent 1: chat + reservation + escalation
│   │   └── admin_agent.py           # Agent 2: approve/refuse via admin API
│   ├── api/
│   │   ├── routes_chat.py           # POST /chat (user-facing)
│   │   ├── routes_admin.py          # GET /admin/reservations, POST /admin/chat
│   │   └── schemas.py               # Pydantic request/response models
│   ├── config.py                    # All environment settings incl. RAG tuning
│   ├── graph/
│   │   └── orchestration.py         # LangGraph pipeline: user → interrupt → approval → write
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
│       ├── reservation.py           # Reservation booking tool
│       ├── escalate_to_admin.py     # Queues reservation for human admin review
│       ├── approve_reservation.py   # Sets reservation status to approved
│       └── refuse_reservation.py    # Sets reservation status to refused
├── mcp_server/
│   └── server.py                    # MCP server — writes confirmed reservations to file
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
ollama pull qwen2.5:7b          # chat model (Agent 1 + Agent) + RAGAS judge
ollama pull nomic-embed-text    # embeddings
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

### Start the MCP server
```bash
uv run python mcp_server/server.py
```

### Start the API server
```bash
uv run uvicorn main:app --reload
```

### Start the frontend
```bash
uv run streamlit run frontend/app.py
```

### Visualise the graph (LangGraph Studio)
```bash
uv run langgraph dev
```
Opens LangGraph Studio at `http://localhost:2024`.

> **Note:** Start the MCP server before running LangGraph Studio, otherwise `write_confirmation` node will fail with a connection error.

> **Note:** LangGraph Studio manages its own persistence — the custom `SqliteSaver` checkpointer is only used when running via FastAPI (`api_graph`). The `orchestration_graph` exported for Studio has no checkpointer.

To test the full pipeline in Studio:
1. Send a message with only `Messages` field — `conversation_id` is auto-generated
2. To make a reservation, fill in the sidebar form in Streamlit and submit, or send reservation details directly as a message
3. When the graph pauses at `wait_for_admin`, use the **Interrupts** panel to resume with `approved` or `refused`

---

## Human-in-the-Loop Flow

The entire pipeline runs as a single LangGraph `StateGraph` with a `SqliteSaver` checkpointer so state survives across the two separate HTTP requests (user → admin).

`user_interaction` node runs `ParkingChatAgent`. If a reservation is detected in SQLite for this `conversation_id`, the graph routes to `wait_for_admin` and calls `interrupt()` — execution pauses and state is persisted.

When the admin sends `POST /admin/chat`, the route looks up the `conversation_id` from the `reservation_id` in SQLite and resumes the graph via `Command(resume=decision)`. The `admin_approval` node runs the appropriate tool, then routing decides whether to call the `write_confirmation` node (approved) or end (refused).

### Admin API endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/admin/reservations` | List all reservations pending approval |
| `POST` | `/admin/chat` | Send a decision message to AdminAgent |

**Example — list pending reservations:**
```bash
curl http://localhost:8000/admin/reservations
```

**Example — approve a reservation:**
```bash
curl -X POST http://localhost:8000/admin/chat \
  -H "Content-Type: application/json" \
  -d '{"reservation_id": "ed7757ae-b834-481f-9a61-93060ce97460", "message": "approved"}'
```

**Example — refuse a reservation:**
```bash
curl -X POST http://localhost:8000/admin/chat \
  -H "Content-Type: application/json" \
  -d '{"reservation_id": "ed7757ae-b834-481f-9a61-93060ce97460", "message": "refused"}'
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
    A[User Message] --> B[GuardRails: injection check + PII scrub]
    B --> C[Agent 1: ParkingChatAgent]
    C --> D[get_parking_information]
    D --> E[Milvus Vector Search]
    E --> F[Retrieved Context]
    F --> C
    C --> G[make_parking_reservation]
    G --> H[SQLite: pending_approval]
    H --> I[escalate_to_admin]
    I --> J[Agent 1 reply to user]
    J --> K[GuardRails: PII filter]

    L[Human Admin] --> M[GET /admin/reservations]
    L --> N[POST /admin/chat]
    N --> O[Agent 2: AdminAgent]
    O --> P[approve_reservation or refuse_reservation]
    P --> Q[SQLite: approved / refused]
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
