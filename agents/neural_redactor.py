"""
Agent 1b — Neural SLM Redactor
Finds contextual / implicit PII that regex rules cannot catch.
Runs AFTER the symbolic rule engine; extends its token map.
"""
import sys
import re
import json
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from config import LOCAL_MODEL_NAME, OLLAMA_BASE_URL
from pipeline.state import PipelineState

SYSTEM_PROMPT = """You are a highly precise PII (Personally Identifiable Information) detection system.
Your ONLY job is to find sensitive information in text that hasn't already been redacted.
Already redacted items appear as [TYPE_N] tokens — do NOT modify or mention these.

Find these types of contextual PII that regex rules might miss:
- Implicit identifiers (e.g., "the only female doctor in Cardiology" identifies a specific person)
- Professional titles with partial names (e.g., "Dr. A.", "Mr. K.")
- Relative references that could identify someone ("my eldest daughter the principal")
- Organization-specific role identifiers ("the department head of Finance")

Respond ONLY with valid JSON in this exact format:
{
  "new_pii_found": [
    {"text": "exact text from document", "type": "PERSON"}
  ],
  "confidence": "high"
}

Allowed types: PERSON, PHONE, EMAIL, LOCATION, OTHER
If no additional PII is found, return: {"new_pii_found": [], "confidence": "high"}
Do NOT invent PII. Do NOT modify existing [TYPE_N] tokens."""


def _get_next_counter(reverse_map: dict) -> dict:
    """Find the highest existing token number for each type."""
    counters: dict[str, int] = {}
    for token in reverse_map:
        m = re.match(r'\[([A-Z_]+)_(\d+)\]', token)
        if m:
            ttype, num = m.group(1), int(m.group(2))
            counters[ttype] = max(counters.get(ttype, 0), num)
    return counters


def _parse_llm_json(raw: str) -> list[dict]:
    """Robustly parse JSON from LLM response."""
    # Try direct parse
    try:
        data = json.loads(raw)
        return data.get("new_pii_found", [])
    except json.JSONDecodeError:
        pass

    # Extract JSON block from markdown fences
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            return data.get("new_pii_found", [])
        except json.JSONDecodeError:
            pass

    # Find first {...} block
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            return data.get("new_pii_found", [])
        except json.JSONDecodeError:
            pass

    return []


def run(state: PipelineState) -> PipelineState:
    """Run neural redactor on already-partially-sanitized text."""
    sanitized = state.get("sanitized_text", "")
    pii_map   = dict(state.get("pii_token_map", {}))
    rev_map   = dict(state.get("reverse_map", {}))
    counts    = dict(state.get("pii_counts", {}))
    errors    = list(state.get("errors", []))

    try:
        from langchain_ollama import ChatOllama
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = ChatOllama(model=LOCAL_MODEL_NAME, base_url=OLLAMA_BASE_URL, temperature=0.0)
        user_msg = f"Analyze this text for unredacted contextual PII:\n\n{sanitized}"
        response = llm.invoke([SystemMessage(content=SYSTEM_PROMPT),
                               HumanMessage(content=user_msg)])
        raw_output = response.content

    except Exception as e:
        errors.append(f"[NeuralRedactor] Ollama error: {e}. Skipping neural pass.")
        state["errors"] = errors
        return state

    new_pii = _parse_llm_json(raw_output)
    if not new_pii:
        state["errors"] = errors
        return state

    type_counters = _get_next_counter(rev_map)
    result = sanitized

    for item in new_pii:
        entity = item.get("text", "").strip()
        ptype  = item.get("type", "OTHER").upper()
        if not entity or entity in pii_map:
            continue
        if entity not in result:
            continue

        # Assign next token
        type_counters[ptype] = type_counters.get(ptype, 0) + 1
        token = f"[{ptype}_{type_counters[ptype]}]"

        pii_map[entity] = token
        rev_map[token]  = entity
        counts[ptype]   = counts.get(ptype, 0) + 1
        result = result.replace(entity, token)

    state["sanitized_text"] = result
    state["pii_token_map"]  = pii_map
    state["reverse_map"]    = rev_map
    state["pii_counts"]     = counts
    state["errors"]         = errors
    return state


def neural_redactor_node(state: PipelineState) -> dict:
    """LangGraph-compatible node wrapper."""
    updated = run(state)
    return {
        "pii_token_map":  updated["pii_token_map"],
        "reverse_map":    updated["reverse_map"],
        "sanitized_text": updated["sanitized_text"],
        "pii_counts":     updated["pii_counts"],
        "errors":         updated["errors"],
    }

