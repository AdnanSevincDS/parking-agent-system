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
            "relevant_doc_ids": item["relevant_doc_ids"],
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
        relevant_ids = item["relevant_doc_ids"]
        hits = sum(1 for doc_id in relevant_ids if doc_id in retrieved_ids)
        recall = hits / len(relevant_ids)
        precision = hits / k
        hit_rate = 1.0 if hits > 0 else 0.0

        results.append({
            "question": item["question"],
            "answer": answer,
            "contexts": [doc.page_content for doc in retrieved_docs],
            "retrieved_doc_ids": ", ".join(retrieved_ids) if retrieved_ids else "none",
            "ground_truth": item["ground_truth"],
            "latency_ms": latency_ms,
            "recall_at_k": round(recall, 4),
            "precision_at_k": round(precision, 4),
            "hit_rate_at_k": hit_rate,
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
    eval_df["question"] = [r["question"] for r in results]
    eval_df["retrieved_doc_ids"] = [r["retrieved_doc_ids"] for r in results]
    eval_df["latency_ms"] = [r["latency_ms"] for r in results]
    eval_df["recall_at_k"] = [r["recall_at_k"] for r in results]
    eval_df["precision_at_k"] = [r["precision_at_k"] for r in results]
    eval_df["hit_rate_at_k"] = [r["hit_rate_at_k"] for r in results]
    return eval_df


def print_summary(df: pd.DataFrame) -> None:
    k = rag_config.top_k
    nan_count = df["faithfulness"].isna().sum()
    print(f"\n{'=' * 45}")
    print("  RAG Evaluation Summary")
    print(f"{'=' * 45}")
    print(f"  Questions          : {len(df)}")
    if nan_count:
        print(f"  Tool not called    : {nan_count} question(s) — RAGAS scores N/A")
    print(f"  Recall@{k}           : {df['recall_at_k'].mean():.2%}")
    print(f"  Precision@{k}        : {df['precision_at_k'].mean():.2%}")
    print(f"  Hit Rate@{k}         : {df['hit_rate_at_k'].mean():.2%}")
    print(f"  Faithfulness       : {df['faithfulness'].mean():.2%}")
    print(f"  Context Precision  : {df['context_precision'].mean():.2%}")
    print(f"  Context Recall     : {df['context_recall'].mean():.2%}")
    print(f"  Avg latency        : {df['latency_ms'].mean():.1f} ms")
    print(f"  Min latency        : {df['latency_ms'].min():.1f} ms")
    print(f"  Max latency        : {df['latency_ms'].max():.1f} ms")
    print(f"{'=' * 45}\n")


def save_csv(df: pd.DataFrame) -> None:
    csv_df = df.copy()
    if "contexts" in csv_df.columns:
        csv_df["contexts"] = csv_df["contexts"].apply(
            lambda x: "\n---\n".join(x) if isinstance(x, list) else x
        )
    csv_path = REPORTS_DIR / "evaluation_results.csv"
    csv_df.to_csv(csv_path, index=False)
    print(f"CSV saved → {csv_path}")


def generate_evidently_report(df: pd.DataFrame) -> None:
    from evidently import Report
    from evidently.presets import DataSummaryPreset

    target_columns = [
        "recall_at_k", "precision_at_k", "hit_rate_at_k",
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

    # Per-question table — show N/A instead of nan
    display_df = df[["question", "retrieved_doc_ids"] + target_columns].copy()
    for col in ["recall_at_k", "precision_at_k", "hit_rate_at_k", "faithfulness", "context_precision", "context_recall"]:
        display_df[col] = display_df[col].apply(
            lambda x: "N/A" if pd.isna(x) else f"{x:.0%}"
        )
    display_df["latency_ms"] = display_df["latency_ms"].map("{:.0f} ms".format)

    table_html = display_df.to_html(index=False, classes="eval-table", border=0)

    inject = f"""
    <div style="padding:24px; font-family:sans-serif;">
        <h2 style="margin-bottom:12px;">Per-Question Results</h2>
        <p style="font-size:12px;color:#888;">N/A = agent did not call the retrieval tool for this question.</p>
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
    dataset = dataset[:1]
    print(f"{len(dataset)} questions loaded.\n")

    agent = ParkingChatAgent()
    eval_df = run_evaluation(agent, dataset)

    print_summary(eval_df)
    save_csv(eval_df)
    generate_evidently_report(eval_df)


if __name__ == "__main__":
    main()
