"""
Evaluation Runner for PrivacySwarm
Computes all 6 metrics on the synthetic dataset.
"""
import sys
import json
import time
import pathlib
import re

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from config import GROQ_API_KEY, CLOUD_MODEL_NAME, SYNTHETIC_DIR


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_dataset(path: str = None) -> list[dict]:
    """Load the synthetic evaluation dataset."""
    p = pathlib.Path(path) if path else SYNTHETIC_DIR / "dataset.json"
    if not p.exists():
        raise FileNotFoundError(
            f"Dataset not found at {p}. Run: python data/generate_dataset.py"
        )
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def compute_pii_leakage_rate(state: dict, ground_truth: list[dict]) -> float:
    """
    % of ground-truth PII entities that are present in sanitized_text
    (i.e., leaked and potentially sent to cloud).
    """
    sanitized = state.get("sanitized_text", "")
    if not ground_truth:
        return 0.0
    leaked = sum(1 for item in ground_truth if item["entity"] in sanitized)
    return round((leaked / len(ground_truth)) * 100, 2)


def compute_pii_detection_recall(state: dict, ground_truth: list[dict]) -> float:
    """
    % of ground-truth PII entities that were caught (tokenized) by the system.
    """
    pii_map = state.get("pii_token_map", {})
    if not ground_truth:
        return 100.0
    caught = sum(1 for item in ground_truth if item["entity"] in pii_map)
    return round((caught / len(ground_truth)) * 100, 2)


def compute_factual_retention(state: dict, original_text: str) -> float:
    """
    ROUGE-1 F1 between final_answer and original_text.
    Higher = more original content preserved.
    """
    final = state.get("final_answer", "")
    if not final or not original_text:
        return 0.0

    try:
        from rouge_score import rouge_scorer as rs
        scorer = rs.RougeScorer(["rouge1"], use_stemmer=True)
        scores = scorer.score(original_text, final)
        return round(scores["rouge1"].fmeasure * 100, 2)
    except ImportError:
        # Fallback: simple word overlap
        orig_words = set(original_text.lower().split())
        final_words = set(final.lower().split())
        if not orig_words:
            return 0.0
        overlap = len(orig_words & final_words) / len(orig_words)
        return round(overlap * 100, 2)


def compute_latency(state: dict) -> float:
    """Return end-to-end latency in seconds."""
    start = state.get("start_time", 0)
    if start:
        return round(time.time() - start, 3)
    return state.get("audit_entry", {}).get("latency_seconds", 0.0)


def _baseline_call(text: str, task: str) -> dict:
    """Monolithic cloud baseline: send raw text directly to cloud."""
    start = time.time()
    result = text  # default fallback

    if GROQ_API_KEY:
        try:
            from langchain_groq import ChatGroq
            from langchain_core.messages import HumanMessage, SystemMessage
            llm = ChatGroq(model=CLOUD_MODEL_NAME, groq_api_key=GROQ_API_KEY, temperature=0.1)
            resp = llm.invoke([
                SystemMessage(content="You are a helpful AI assistant."),
                HumanMessage(content=f"Context:\n{text}\n\nTask: {task}"),
            ])
            result = resp.content
        except Exception as e:
            result = f"[Baseline error: {e}]"

    return {
        "final_answer":   result,
        "sanitized_text": text,          # No redaction in baseline
        "pii_token_map":  {},
        "routing_decision": "cloud",
        "start_time":     start,
        "pii_counts":     {},
        "audit_entry":    {},
    }


# ── Main evaluation loop ──────────────────────────────────────────────────────

def run_full_evaluation(
    n_docs: int = 20,
    baseline_mode: bool = False,
    task: str = "Summarize this document concisely.",
) -> dict:
    """
    Run evaluation on n_docs documents.
    baseline_mode=True → skip the pipeline, call cloud directly.
    Returns a dict with all metrics.
    """
    from pipeline.graph import run_pipeline

    dataset = load_dataset()[:n_docs]
    mode    = "baseline" if baseline_mode else "privacyswarm"

    per_doc = []
    routing_local = 0
    routing_cloud = 0
    hallucination_flags = 0
    total_validation_attempts = 0

    print(f"\n{'='*60}")
    print(f"  PrivacySwarm Evaluation — Mode: {mode.upper()} ({n_docs} docs)")
    print(f"{'='*60}")

    for i, doc in enumerate(dataset, 1):
        raw_text   = doc["text"]
        ground_truth = doc.get("ground_truth_pii", [])

        print(f"  [{i:03d}/{n_docs}] {doc['id']} ({doc['category']}) ... ", end="", flush=True)
        t0 = time.time()

        if baseline_mode:
            state = _baseline_call(raw_text, task)
        else:
            try:
                state = run_pipeline(raw_text, task)
            except Exception as e:
                print(f"ERROR: {e}")
                per_doc.append({"id": doc["id"], "error": str(e)})
                continue

        latency  = round(time.time() - t0, 2)
        leakage  = compute_pii_leakage_rate(state, ground_truth)
        recall   = compute_pii_detection_recall(state, ground_truth)
        retention = compute_factual_retention(state, raw_text)

        rd = state.get("routing_decision", "")
        if rd == "local":
            routing_local += 1
        else:
            routing_cloud += 1

        if state.get("hallucination_detected", False):
            hallucination_flags += 1
        total_validation_attempts += state.get("validation_attempts", 0)

        per_doc.append({
            "id":               doc["id"],
            "category":         doc["category"],
            "pii_count":        doc["pii_count"],
            "pii_leakage":      leakage,
            "pii_recall":       recall,
            "factual_retention": retention,
            "latency_s":        latency,
            "routing":          rd,
            "hallucination":    state.get("hallucination_detected", False),
            "validation_attempts": state.get("validation_attempts", 0),
        })
        print(f"leak={leakage:.0f}% recall={recall:.0f}% retain={retention:.0f}% {latency:.1f}s")

    valid_docs = [d for d in per_doc if "error" not in d]
    n_valid = len(valid_docs) or 1

    results = {
        "mode":                     mode,
        "n_docs":                   n_docs,
        "n_valid":                  n_valid,
        "avg_pii_leakage_rate":     round(sum(d["pii_leakage"] for d in valid_docs) / n_valid, 2),
        "avg_pii_detection_recall": round(sum(d["pii_recall"] for d in valid_docs) / n_valid, 2),
        "avg_factual_retention":    round(sum(d["factual_retention"] for d in valid_docs) / n_valid, 2),
        "avg_latency_seconds":      round(sum(d["latency_s"] for d in valid_docs) / n_valid, 2),
        "routing_breakdown":        {"local": routing_local, "cloud": routing_cloud},
        "hallucination_rate":       round((hallucination_flags / n_valid) * 100, 1),
        "avg_validation_attempts":  round(total_validation_attempts / n_valid, 2),
        "per_doc_results":          per_doc,
    }

    print(f"\n{'='*60}")
    print(f"  SUMMARY — {mode.upper()}")
    print(f"{'='*60}")
    print(f"  PII Leakage Rate   : {results['avg_pii_leakage_rate']:.1f}%  (lower=better)")
    print(f"  PII Detection Recall: {results['avg_pii_detection_recall']:.1f}%  (higher=better)")
    print(f"  Factual Retention  : {results['avg_factual_retention']:.1f}%  (higher=better)")
    print(f"  Avg Latency        : {results['avg_latency_seconds']:.2f}s")
    print(f"  Routing: local={routing_local} cloud={routing_cloud}")
    print(f"  Hallucination Rate : {results['hallucination_rate']:.1f}%")
    print(f"{'='*60}\n")

    return results


def save_results(results: dict, path: str = None) -> str:
    """Save results dict to JSON. Returns the saved file path."""
    out_dir = pathlib.Path(__file__).parent
    out_dir.mkdir(exist_ok=True)
    ts   = time.strftime("%Y%m%d_%H%M%S")
    name = path or str(out_dir / f"results_{ts}.json")
    with open(name, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to: {name}")
    return name


if __name__ == "__main__":
    r = run_full_evaluation(n_docs=10, baseline_mode=False)
    save_results(r)

