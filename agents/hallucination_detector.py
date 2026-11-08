"""
Agent 4 — Hallucination Detector
Two-layer check before re-insertion:
  Check 1 (Symbolic): Verifies all [TYPE_N] tokens in the response exist in the reverse_map.
  Check 2 (Neural):   Semantic check for cloud responses to catch logical hallucinations.
"""
import sys
import re
import json
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from config import MAX_HALLUCINATION_RETRIES, LOCAL_MODEL_NAME, OLLAMA_BASE_URL
from pipeline.state import PipelineState

HALLUCINATION_CHECK_SYSTEM = """You are a strict AI response validator.
Given a context, a task, and an AI-generated response, determine if the response
contains hallucinated (invented) information not found in the context.

Respond ONLY with valid JSON:
{"is_hallucination": true_or_false, "reason": "one sentence explanation or null"}"""


def _find_invalid_tokens(response: str, reverse_map: dict) -> list[str]:
    """
    Find [TYPE_N] tokens in the response that don't exist in the reverse_map.
    These are tokens invented by the AI.
    """
    found_tokens = re.findall(r'\[[A-Z_]+_\d+\]', response)
    invalid = [t for t in found_tokens if t not in reverse_map]
    return list(set(invalid))


def _neural_hallucination_check(state: PipelineState, errors: list) -> tuple:
    """Call local SLM to check for semantic hallucinations."""
    from langchain_core.messages import HumanMessage, SystemMessage

    context  = state.get("sanitized_text", "")[:600]
    task     = state.get("task_description", "")
    response = state.get("raw_response", "")

    user_msg = (
        f"Context (first 600 chars):\n{context}\n\n"
        f"Task: {task}\n\n"
        f"AI Response:\n{response}"
    )

    try:
        from langchain_ollama import ChatOllama
        llm = ChatOllama(model=LOCAL_MODEL_NAME, base_url=OLLAMA_BASE_URL, temperature=0.0)
        resp = llm.invoke([
            SystemMessage(content=HALLUCINATION_CHECK_SYSTEM),
            HumanMessage(content=user_msg),
        ])
        raw = resp.content
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            data   = json.loads(m.group())
            is_hal = bool(data.get("is_hallucination", False))
            reason = data.get("reason")
            return is_hal, reason
    except Exception as e:
        errors.append(f"[HallucinationDetector] Neural check error: {e}")

    return False, None


def run(state: PipelineState) -> PipelineState:
    """Run the hallucination detection pipeline."""
    response    = state.get("raw_response", "")
    rev_map     = state.get("reverse_map", {})
    source      = state.get("response_source", "local_swarm")
    retry_count = state.get("hallucination_retry_count", 0)
    errors      = list(state.get("errors", []))

    # ── Check 1: Symbolic token validation ───────────────────────────────────
    invalid = _find_invalid_tokens(response, rev_map)
    if invalid:
        state["hallucination_detected"] = True
        state["hallucination_reason"]   = f"AI invented non-existent tokens: {invalid}"
        state["hallucination_retry_count"] = retry_count + 1
        state["errors"] = errors
        return state

    # ── Check 2: Neural semantic check (cloud responses, first attempt only) ─
    if source == "cloud" and retry_count == 0:
        is_hal, reason = _neural_hallucination_check(state, errors)
        if is_hal:
            state["hallucination_detected"] = True
            state["hallucination_reason"]   = reason or "Semantic hallucination detected"
            state["hallucination_retry_count"] = retry_count + 1
            state["errors"] = errors
            return state

    # All checks passed
    state["hallucination_detected"]    = False
    state["hallucination_reason"]      = None
    state["hallucination_retry_count"] = retry_count
    state["errors"]                    = errors
    return state


def hallucination_route(state: PipelineState) -> str:
    """
    LangGraph conditional edge.
    Returns 'pass', 'retry_local', or 'retry_cloud'.
    """
    if not state.get("hallucination_detected", False):
        return "pass"

    if state.get("hallucination_retry_count", 0) >= MAX_HALLUCINATION_RETRIES:
        return "pass"  # Give up — pass whatever we have

    source = state.get("response_source", "local_swarm")
    return "retry_local" if source == "local_swarm" else "retry_cloud"


def hallucination_detector_node(state: PipelineState) -> dict:
    """LangGraph-compatible node wrapper."""
    updated = run(state)
    return {
        "hallucination_detected":    updated["hallucination_detected"],
        "hallucination_reason":      updated["hallucination_reason"],
        "hallucination_retry_count": updated["hallucination_retry_count"],
        "errors":                    updated["errors"],
    }

