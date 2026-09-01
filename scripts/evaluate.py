"""RAG evaluation: RAGAS metrics + Recall@K + Precision@K + latency + Evidently report."""
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

# RAGAS patch — redirect old vertexai module path if available
try:
    import langchain_google_vertexai
    if "langchain_community.chat_models" not in sys.modules:
        sys.modules["langchain_community.chat_models"] = types.ModuleType(
            "langchain_community.chat_models"
        )
    sys.modules["langchain_community.chat_models.vertexai"] = langchain_google_vertexai
except ImportError:
    pass

from ragas import evaluate
from ragas.metrics import faithfulness, context_precision, context_recall
from langchain_ollama import ChatOllama, OllamaEmbeddings
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from datasets import Dataset


def load_dataset(path: Path) -> list[dict]:
    with open(path) as f:
        data = yaml.safe_load(f)
    return [
        {
            "question": item["question"],
            "ground_truth": item["reference_answer"],
            "relevant_doc_id": item["relevant_doc_id"],
        }
        for item in data["qa_pairs"]
    ]


def run_evaluation(agent: ParkingChatAgent, eval_data: list[dict]) -> pd.DataFrame:
    results = []
    k = rag_config.top_k

    print(f"Running {len(eval_data)} questions through the agent (K={k})...")
    for item in eval_data:
        start = time.perf_counter()
        answer, retrieved_docs = agent.run(item["question"], uuid4())
        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        retrieved_ids = [doc.metadata.get("document_id") for doc in retrieved_docs]
        is_hit = item["relevant_doc_id"] in retrieved_ids

        results.append({
            "question": item["question"],
            "answer": answer,
            "contexts": [doc.page_content for doc in retrieved_docs],
            "ground_truth": item["ground_truth"],
            "latency_ms": latency_ms,
            "recall_at_k": 1.0 if is_hit else 0.0,
            "precision_at_k": round(1 / k if is_hit else 0.0, 4),
        })
        print(f"  ✓ {item['question'][:60]}  ({latency_ms:.0f} ms)")

    ragas_dataset = Dataset.from_list(results)

    print("\nEvaluating with local Ollama judge...")
    ragas_llm = LangchainLLMWrapper(
        ChatOllama(
            model=settings.model,
            base_url=settings.ollama_base_url,
            temperature=rag_config.temperature,
        )
    )
    ragas_embeddings = LangchainEmbeddingsWrapper(
        OllamaEmbeddings(
            model=rag_config.embedding_model,
            base_url=settings.ollama_base_url,
        )
    )

    evaluation_result = evaluate(
        dataset=ragas_dataset,
        metrics=[faithfulness, context_precision, context_recall],
        llm=ragas_llm,
        embeddings=ragas_embeddings,
    )

    eval_df = evaluation_result.to_pandas()
    eval_df["latency_ms"] = [r["latency_ms"] for r in results]
    eval_df["recall_at_k"] = [r["recall_at_k"] for r in results]
    eval_df["precision_at_k"] = [r["precision_at_k"] for r in results]
    eval_df["question"] = [r["question"] for r in results]
    return eval_df


def print_summary(df: pd.DataFrame) -> None:
    k = rag_config.top_k
    print(f"\n{'=' * 45}")
    print("  RAG Evaluation Summary")
    print(f"{'=' * 45}")
    print(f"  Questions          : {len(df)}")
    print(f"  Recall@{k}           : {df['recall_at_k'].mean():.2%}")
    print(f"  Precision@{k}        : {df['precision_at_k'].mean():.2%}")
    print(f"  Faithfulness       : {df['faithfulness'].mean():.2%}")
    print(f"  Context Precision  : {df['context_precision'].mean():.2%}")
    print(f"  Context Recall     : {df['context_recall'].mean():.2%}")
    print(f"  Avg latency        : {df['latency_ms'].mean():.1f} ms")
    print(f"  Min latency        : {df['latency_ms'].min():.1f} ms")
    print(f"  Max latency        : {df['latency_ms'].max():.1f} ms")
    print(f"{'=' * 45}\n")


def generate_evidently_report(df: pd.DataFrame) -> None:
    from evidently import Report
    from evidently.presets import DataSummaryPreset

    target_columns = [
        "recall_at_k", "precision_at_k",
        "faithfulness", "context_precision", "context_recall",
        "latency_ms",
    ]
    report_df = df[target_columns].copy()

    report = Report(metrics=[DataSummaryPreset(columns=target_columns)])
    snapshot = report.run(report_df, None)

    REPORTS_DIR.mkdir(exist_ok=True)
    report_path = REPORTS_DIR / "evaluation_report.html"

    result = snapshot if snapshot is not None else report
    result.save_html(str(report_path))

    # Inject per-question table
    display_df = df[["question"] + target_columns].copy()
    for col in ["recall_at_k", "precision_at_k", "faithfulness", "context_precision", "context_recall"]:
        display_df[col] = display_df[col].map("{:.0%}".format)
    display_df["latency_ms"] = display_df["latency_ms"].map("{:.0f} ms".format)

    table_html = display_df.to_html(index=False, classes="eval-table", border=0)

    inject = f"""
    <div style="padding:24px; font-family:sans-serif;">
        <h2 style="margin-bottom:12px;">Per-Question Results</h2>
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
    dataset = dataset[:2]
    print(f"{len(dataset)} questions loaded.\n")

    agent = ParkingChatAgent()
    eval_df = run_evaluation(agent, dataset)

    print_summary(eval_df)
    generate_evidently_report(eval_df)


if __name__ == "__main__":
    main()
