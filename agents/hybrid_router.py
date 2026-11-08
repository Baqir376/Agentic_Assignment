"""
Agent 2 — Hybrid Router (Neuro-Symbolic)
Stage 1: Symbolic rules (instant, free)
Stage 2: Neural complexity scoring (only when Stage 1 is inconclusive)
"""
import sys
import re
import json
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from config import (
    COMPLEX_KEYWORDS, SIMPLE_KEYWORDS, SENSITIVE_TOPICS,
    COMPLEXITY_THRESHOLD, LOCAL_MODEL_NAME, OLLAMA_BASE_URL,
)
from pipeline.state import PipelineState


# ── Stage 1: Symbolic routing ─────────────────────────────────────────────────

def _stage1_symbolic(sanitized_text: str, task: str) -> tuple:
    """
    Returns (decision, reason, sensitivity_flagged).
    decision is None if rules cannot decide → defer to Stage 2.
    """
    combined = (sanitized_text[:300] + " " + task).lower()

    # 1. Check sensitive topics → ALWAYS local
    for topic in SENSITIVE_TOPICS:
        if topic in combined:
            return "local", f"Sensitive topic detected: '{topic}' — forced local", True

    word_count = len(sanitized_text.split())

    # 2. Simple task + short text → local
    for kw in SIMPLE_KEYWORDS:
        if kw in task.lower() and word_count <= 300:
            return "local", f"Simple task keyword '{kw}' and short text ({word_count}w)", False

    # 3. Complex keywords → cloud
    for kw in COMPLEX_KEYWORDS:
        if kw in task.lower() or kw in sanitized_text[:200].lower():
            return "cloud", f"Complex keyword '{kw}' detected", False

    # 4. Very short text → local
    if word_count < 40:
        return "local", f"Very short document ({word_count} words)", False

    # Cannot decide
    return None, "Symbolic rules inconclusive — deferring to neural stage", False


# ── Stage 2: Neural complexity scoring ───────────────────────────────────────

ROUTER_SYSTEM = """You are a task complexity classifier.
Rate the complexity of a task on a scale from 0.0 to 1.0:
- 0.0 = simple formatting, extraction, translation, or summarization
- 1.0 = complex medical diagnosis, legal interpretation, multi-step reasoning, or analysis

Respond ONLY with valid JSON: {"complexity_score": 0.X, "reason": "brief one-line explanation"}
No other text. No markdown fences."""


def _stage2_neural(sanitized_text: str, task: str, errors: list) -> tuple:
    """
    Returns (decision, reason, stage).
    """
    preview = sanitized_text[:300].strip()
    user_msg = f"Task: {task}\nDocument preview (first 300 chars): {preview}"

    try:
        from langchain_ollama import ChatOllama
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = ChatOllama(model=LOCAL_MODEL_NAME, base_url=OLLAMA_BASE_URL, temperature=0.0)
        resp = llm.invoke([SystemMessage(content=ROUTER_SYSTEM),
                           HumanMessage(content=user_msg)])
        raw = resp.content

        # Parse
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            data = json.loads(m.group())
            score  = float(data.get("complexity_score", 0.5))
            reason = data.get("reason", "Neural scoring")
        else:
            score, reason = 0.5, "Could not parse neural score — defaulting to 0.5"

    except Exception as e:
        errors.append(f"[Router/Stage2] Neural scoring error: {e}. Defaulting to local.")
        return "local", "Neural scoring failed — defaulting to local", "neural"

    if score >= COMPLEXITY_THRESHOLD:
        return "cloud", f"Neural score {score:.2f} ≥ {COMPLEXITY_THRESHOLD} → cloud. {reason}", "neural"
    return "local", f"Neural score {score:.2f} < {COMPLEXITY_THRESHOLD} → local. {reason}", "neural"


# ── Main run ──────────────────────────────────────────────────────────────────

def run(state: PipelineState) -> PipelineState:
    """Determine routing decision for the sanitized text."""
    sanitized = state.get("sanitized_text", "")
    task      = state.get("task_description", "process this text")
    errors    = list(state.get("errors", []))

    # Stage 1
    decision, reason, sensitive = _stage1_symbolic(sanitized, task)

    if decision is not None:
        state["routing_decision"]   = decision
        state["routing_reason"]     = reason
        state["routing_stage"]      = "symbolic"
        state["sensitivity_flagged"] = sensitive
        state["errors"]             = errors
        return state

    # Stage 2
    decision, reason, stage = _stage2_neural(sanitized, task, errors)
    state["routing_decision"]   = decision
    state["routing_reason"]     = reason
    state["routing_stage"]      = stage
    state["sensitivity_flagged"] = False
    state["errors"]             = errors
    return state


def router_route(state: PipelineState) -> str:
    """LangGraph conditional edge: returns 'local' or 'cloud'."""
    return state.get("routing_decision", "local")


def hybrid_router_node(state: PipelineState) -> dict:
    """LangGraph-compatible node wrapper."""
    updated = run(state)
    return {
        "routing_decision":    updated["routing_decision"],
        "routing_reason":      updated["routing_reason"],
        "routing_stage":       updated["routing_stage"],
        "sensitivity_flagged": updated["sensitivity_flagged"],
        "errors":              updated["errors"],
    }

