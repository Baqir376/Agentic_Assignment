"""
PrivacySwarm Pipeline State Schema
-----------------------------------
This is the SINGLE SOURCE OF TRUTH for the state passed between all agents.
Every agent reads from and writes to this TypedDict.
"""
from typing import TypedDict, Optional, List, Dict, Any


class PipelineState(TypedDict):
    # ── INPUT ──────────────────────────────────────────────────────────────
    raw_text: str                        # Original user input with real PII
    task_description: str               # What the user wants done (e.g. "summarize")

    # ── AFTER AGENTS 1a + 1b (PII Detection) ──────────────────────────────
    pii_token_map: Dict[str, str]        # real_pii → token: {"John Doe": "[PERSON_1]"}
    reverse_map: Dict[str, str]          # token → real_pii: {"[PERSON_1]": "John Doe"}
    sanitized_text: str                  # Text with all PII replaced by tokens
    pii_counts: Dict[str, int]           # {"PERSON": 2, "PHONE": 1, ...}

    # ── AFTER SYMBOLIC VALIDATOR ───────────────────────────────────────────
    validation_passed: bool
    validation_attempts: int             # How many redaction attempts were made

    # ── AFTER ROUTER (Agent 2) ─────────────────────────────────────────────
    routing_decision: str                # "local" or "cloud"
    routing_reason: str                  # Human-readable explanation
    routing_stage: str                   # "symbolic" or "neural" (which stage decided)
    sensitivity_flagged: bool           # True if sensitive topic → force local

    # ── AFTER RESPONSE (Agent 3 local OR cloud) ────────────────────────────
    raw_response: str                    # Response still using token placeholders
    response_source: str                 # "local_swarm" or "cloud"
    debate_rounds: int                   # How many debate rounds (local path only)

    # ── AFTER HALLUCINATION DETECTOR (Agent 4) ─────────────────────────────
    hallucination_detected: bool
    hallucination_reason: Optional[str]
    hallucination_retry_count: int

    # ── AFTER RE-INSERTER (Agent 5) ────────────────────────────────────────
    final_answer: str                    # Final answer with real names restored

    # ── AUDIT & ERRORS ─────────────────────────────────────────────────────
    audit_entry: Dict[str, Any]          # Everything to log to SQLite
    errors: List[str]                    # Non-fatal errors encountered
    start_time: float                    # Unix timestamp when pipeline started


def initial_state(raw_text: str, task_description: str) -> PipelineState:
    """Create a fresh state with all defaults set."""
    import time
    return PipelineState(
        raw_text=raw_text,
        task_description=task_description,
        pii_token_map={},
        reverse_map={},
        sanitized_text="",
        pii_counts={},
        validation_passed=False,
        validation_attempts=0,
        routing_decision="",
        routing_reason="",
        routing_stage="",
        sensitivity_flagged=False,
        raw_response="",
        response_source="",
        debate_rounds=0,
        hallucination_detected=False,
        hallucination_reason=None,
        hallucination_retry_count=0,
        final_answer="",
        audit_entry={},
        errors=[],
        start_time=time.time(),
    )

