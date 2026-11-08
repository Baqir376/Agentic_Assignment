"""
Symbolic Validator Engine
Post-redaction verification gate.
Re-runs all regex and dictionary checks on the sanitized text.
If any real PII is detected → validation fails → retry neural redactor.
"""
import sys
import re
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from config import MAX_VALIDATION_ATTEMPTS
from agents.symbolic_rule_engine import (
    PATTERNS, _find_regex_matches, _find_dict_matches, _resolve_overlaps
)
from pipeline.state import PipelineState


def _text_contains_unredacted_pii(sanitized_text: str, reverse_map: dict) -> list:
    """
    Check whether sanitized_text still contains detectable raw PII.
    Returns a list of problematic strings found (empty if clean).
    """
    # Temporarily un-token the text to check: replace tokens with placeholders
    # so regex doesn't accidentally match inside a token's digits
    check_text = sanitized_text
    for token in reverse_map:
        check_text = check_text.replace(token, " " * len(token))

    regex_hits = _find_regex_matches(check_text)
    dict_hits  = _find_dict_matches(check_text)
    all_hits   = _resolve_overlaps(regex_hits + dict_hits)

    return [h["entity"].strip() for h in all_hits if h["entity"].strip()]


def run(state: PipelineState) -> PipelineState:
    """
    Validate that sanitized_text is clean of detectable PII.
    Updates validation_passed and validation_attempts in state.
    """
    attempts = state.get("validation_attempts", 0) + 1
    state["validation_attempts"] = attempts

    leaks = _text_contains_unredacted_pii(
        state.get("sanitized_text", ""),
        state.get("reverse_map", {}),
    )

    if leaks:
        state["validation_passed"] = False
        errors = list(state.get("errors", []))
        errors.append(f"[Validator attempt {attempts}] Unredacted PII still found: {leaks[:5]}")
        state["errors"] = errors
    else:
        state["validation_passed"] = True

    return state


def validator_route(state: PipelineState) -> str:
    """
    LangGraph conditional edge router.
    Returns 'retry', 'proceed', or 'blocked' after exhausted failed checks.
    """
    if not state.get("validation_passed", False):
        if state.get("validation_attempts", 0) < MAX_VALIDATION_ATTEMPTS:
            return "retry"
        return "blocked"
    return "proceed"


def symbolic_validator_node(state: PipelineState) -> dict:
    """LangGraph-compatible node wrapper."""
    updated = run(state)
    return {
        "validation_passed":  updated["validation_passed"],
        "validation_attempts": updated["validation_attempts"],
        "errors":             updated["errors"],
    }

