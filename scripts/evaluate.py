"""RAG evaluation: RAGAS metrics + Recall@K + Precision@K + latency + Evidently report."""
import os
import sys
import time
import types
import logging
from pathlib import Path
from uuid import uuid4

import yaml
import pandas as pd
from parking_agent_system.telemetry import setup_phoenix_telemetry
from parking_agent_system.agents.user_agent import ParkingChatAgent
from parking_agent_system.config import settings
from parking_agent_system.config_rag import rag_config

logger = logging.getLogger(__name__)

EVAL_DATASET_PATH = Path(__file__).parent.parent / "data" / "evaluation_dataset.yaml"
REPORTS_DIR = Path(__file__).parent.parent / "reports"

# RAGAS tuning
RAISE_EVAL_EXCEPTIONS = True  # False in prod so one slow row won't kill the run
os.environ.setdefault("RAGAS_CONCURRENCY", "1")  # avoid local Ollama timeouts

# Columns from run_agent() that we merge back onto the RAGAS output DataFrame.
EXTRA_COLUMNS = [
    "retrieved_doc_ids", "reference_doc_ids", "reference_context",
    "latency_ms", "recall_at_k", "precision_at_k",
]

# Metric columns used by the summary printout and the Evidently report.
METRIC_COLUMNS = [
    "recall_at_k", "precision_at_k",
    "faithfulness", "context_precision", "context_recall",
    "latency_ms",
]


def _patch_ragas_vertexai_import() -> None:
    """Redirect the legacy `langchain_community.chat_models.vertexai` path RAGAS still touches."""
    try:
        import langchain_google_vertexai
    except ImportError:
        return
    sys.modules.setdefault(
        "langchain_community.chat_models",
        types.ModuleType("langchain_community.chat_models"),
    )
    sys.modules["langchain_community.chat_models.vertexai"] = langchain_google_vertexai


_patch_ragas_vertexai_import()

from ragas import evaluate
from ragas.metrics import faithfulness, context_precision, context_recall
from langchain_ollama import ChatOllama, OllamaEmbeddings
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.run_config import RunConfig
from datasets import Dataset


def load_dataset(path: Path) -> list[dict]:
    with open(path) as f:
        data = yaml.safe_load(f)
    return [
        {
            "question": item["question"],
            "reference_answer": item["reference_answer"],
            "reference_context": item.get("context", ""),
            "relevant_doc_ids": item["relevant_doc_ids"],
        }
        for item in data["qa_pairs"]
    ]


def run_agent(agent: ParkingChatAgent, eval_data: list[dict]) -> list[dict]:
    """Run each question through the agent and compute retrieval + latency metrics."""
    k = rag_config.top_k
    print(f"Running {len(eval_data)} questions through the agent (K={k})...")

    results = []
    for item in eval_data:
        start = time.perf_counter()
        answer, retrieved_docs = agent.run(item["question"], uuid4())
        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        retrieved_ids = [doc.metadata.get("document_id") for doc in retrieved_docs]
        relevant_ids = item["relevant_doc_ids"]
        hits = sum(1 for doc_id in relevant_ids if doc_id in retrieved_ids)
        recall = hits / len(relevant_ids) if relevant_ids else 0.0

        results.append({
            "question": item["question"],
            "answer": answer,
            "contexts": [doc.page_content for doc in retrieved_docs],
            "retrieved_doc_ids": ", ".join(retrieved_ids) if retrieved_ids else "none",
            "reference_doc_ids": ", ".join(relevant_ids),
            "reference_context": item["reference_context"],
            "reference_answer": item["reference_answer"],
            "latency_ms": latency_ms,
            "recall_at_k": round(recall, 4),
            "precision_at_k": round(hits / min(k, len(relevant_ids)), 4) if relevant_ids else 0.0,
        })
        print(f"  ✓ {item['question'][:60]}  ({latency_ms:.0f} ms)")

    return results


def run_ragas(results: list[dict]) -> pd.DataFrame:
    """Score agent results with RAGAS and merge retrieval metrics back in."""
    print("\nEvaluating with local Ollama judge...")

    ragas_llm = LangchainLLMWrapper(
        ChatOllama(
            model=settings.model_eval,
            base_url=settings.ollama_base_url,
            temperature=0.0,
            num_ctx=settings.llm_context_window,
            num_predict=settings.llm_max_output_tokens,
            format="json",
            timeout=600.0,  # LangChain/HTTP layer timeout
        )
    )
    ragas_embeddings = LangchainEmbeddingsWrapper(
        OllamaEmbeddings(
            model=rag_config.embedding_model,
            base_url=settings.ollama_base_url,
        )
    )

    evaluation_result = evaluate(
        dataset=Dataset.from_list(results),
        metrics=[faithfulness, context_precision, context_recall],
        llm=ragas_llm,
        embeddings=ragas_embeddings,
        column_map={
            "user_input": "question",
            "response": "answer",
            "retrieved_contexts": "contexts",
            "reference": "reference_answer",
        },
        run_config=RunConfig(timeout=600, max_retries=1),
        raise_exceptions=RAISE_EVAL_EXCEPTIONS,
    )

    eval_df = evaluation_result.to_pandas()
    extras = pd.DataFrame(results)[EXTRA_COLUMNS].reset_index(drop=True)
    return pd.concat([eval_df, extras], axis=1)


def print_summary(df: pd.DataFrame) -> None:
    k = rag_config.top_k
    print(f"\n{'=' * 45}")
    print("  RAG Evaluation Summary")
    print(f"{'=' * 45}")
    print(f"  Questions          : {len(df)}")
    print(f"  Recall@{k}           : {df['recall_at_k'].mean():.2%}")
    print(f"  Precision@{k}        : {df['precision_at_k'].mean():.2%}  (normalized: hits / min(K, relevant_docs))")
    print(f"  Faithfulness       : {df['faithfulness'].mean():.2%}")
    print(f"  Context Precision  : {df['context_precision'].mean():.2%}")
    print(f"  Context Recall     : {df['context_recall'].mean():.2%}")
    print(f"  Avg latency        : {df['latency_ms'].mean():.1f} ms")
    print(f"  Min latency        : {df['latency_ms'].min():.1f} ms")
    print(f"  Max latency        : {df['latency_ms'].max():.1f} ms")
    print(f"{'=' * 45}\n")


def save_csv(df: pd.DataFrame) -> None:
    csv_df = df.copy()
    if "retrieved_contexts" in csv_df.columns:
        csv_df["retrieved_contexts"] = csv_df["retrieved_contexts"].apply(
            lambda x: "\n---\n".join(x) if isinstance(x, list) else x
        )
    csv_path = REPORTS_DIR / "evaluation_results.csv"
    csv_df.to_csv(csv_path, index=False)
    print(f"CSV saved → {csv_path}")


def generate_evidently_report(df: pd.DataFrame) -> None:
    from evidently import Report
    from evidently.presets import DataSummaryPreset

    report_df = df[METRIC_COLUMNS].copy()

    report = Report(metrics=[DataSummaryPreset(columns=METRIC_COLUMNS)])
    snapshot = report.run(report_df, None)

    REPORTS_DIR.mkdir(exist_ok=True)
    report_path = REPORTS_DIR / "evaluation_report.html"
    snapshot.save_html(str(report_path))

    display_df = df[["user_input"] + METRIC_COLUMNS].copy()
    display_df["latency_ms"] = display_df["latency_ms"].map("{:.0f} ms".format)
    table_html = display_df.to_html(index=False, classes="eval-table", border=0)

    inject = f"""
    <div style="padding:24px; font-family:sans-serif;">
        <h2 style="margin-bottom:8px;">Per-Question Results</h2>
        <p style="font-size:12px;color:#888;margin-bottom:12px;">
            <b>Precision@K</b> is normalized: <code>hits / min(K, num_relevant_docs)</code>.
            This avoids the misleading 1/K floor when a question has only one labeled relevant document.
        </p>
        <style>
            .eval-table {{ border-collapse:collapse; width:100%; font-size:13px; }}
            .eval-table th, .eval-table td {{ border:1px solid #ddd; padding:8px; text-align:left; }}
            .eval-table th {{ background:#f2f2f2; font-weight:600; }}
            .eval-table tr:nth-child(even) {{ background:#f9f9f9; }}
        </style>
        {table_html}
    </div>
    """

    html = report_path.read_text(encoding="utf-8")
    report_path.write_text(html.replace("</body>", inject + "</body>"), encoding="utf-8")

    print(f"Evidently report saved → {report_path}")


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    setup_phoenix_telemetry()

    print("Loading evaluation dataset...")
    dataset = load_dataset(EVAL_DATASET_PATH)
    print(f"{len(dataset)} questions loaded.\n")

    agent = ParkingChatAgent()
    results = run_agent(agent, dataset)
    eval_df = run_ragas(results)

    print_summary(eval_df)
    save_csv(eval_df)
    generate_evidently_report(eval_df)


if __name__ == "__main__":
    main()
