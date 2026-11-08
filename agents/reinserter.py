"""
Agent 5 — Re-Inserter  (100% symbolic — deterministic dictionary lookup)
Also contains the Cloud Processor node for the cloud routing path.
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from config import GROQ_API_KEY, CLOUD_MODEL_NAME
from pipeline.state import PipelineState

CLOUD_SYSTEM = """You are a helpful AI assistant.
Answer the task using ONLY the information in the provided context.
Preserve any [TYPE_N] tokens EXACTLY as they appear in the context — never replace or omit them.
Do NOT fabricate information not present in the context.
Be thorough and accurate."""


# ── Cloud Processor ───────────────────────────────────────────────────────────

def cloud_processor_node(state: "PipelineState") -> dict:
    """
    Calls the cloud LLM (Groq) with the sanitized text.
    This is used when the router sends the task to the cloud path.
    """
    errors = list(state.get("errors", []))

    if not state.get("validation_passed", False):
        return {"raw_response": "", "response_source": "blocked",
                "errors": errors + ["Cloud processing blocked because redaction validation did not pass."]}

    # Instructions are sent alongside the sanitized document. Reject detectable
    # identifiers here rather than sending an unredacted instruction to a provider.
    from agents.symbolic_validator import _text_contains_unredacted_pii
    if _text_contains_unredacted_pii(state.get("task_description", ""), {}):
        return {"raw_response": "", "response_source": "blocked",
                "errors": errors + ["Cloud processing blocked: remove personal identifiers from the instruction and retry."]}

    if not GROQ_API_KEY:
        errors.append("[CloudProcessor] GROQ_API_KEY not set. No answer was generated.")
        return {
            "raw_response":    "",
            "response_source": "cloud",
            "errors":          errors,
        }

    user_msg = (
        f"Context:\n{state.get('sanitized_text', '')}\n\n"
        f"Task: {state.get('task_description', 'Summarize this document.')}"
    )

    try:
        from langchain_groq import ChatGroq
        from langchain_core.messages import HumanMessage, SystemMessage

        llm  = ChatGroq(model=CLOUD_MODEL_NAME, groq_api_key=GROQ_API_KEY, temperature=0.1)
        resp = llm.invoke([SystemMessage(content=CLOUD_SYSTEM),
                           HumanMessage(content=user_msg)])
        raw  = resp.content

    except Exception as e:
        raw = ""
        errors.append(f"[CloudProcessor] {e}")

    return {"raw_response": raw, "response_source": "cloud", "errors": errors}


# ── Re-Inserter ───────────────────────────────────────────────────────────────

def run(state: PipelineState) -> PipelineState:
    """
    Replace [TYPE_N] tokens back with real PII using reverse_map.
    Pure symbolic — no AI, 100% deterministic.
    """
    result  = state.get("raw_response", "")
    rev_map = state.get("reverse_map", {})

    # Sort by token length descending to avoid [PERSON_1] matching inside [PERSON_10]
    for token in sorted(rev_map.keys(), key=len, reverse=True):
        result = result.replace(token, rev_map[token])

    state["final_answer"] = result
    return state


def reinserter_node(state: PipelineState) -> dict:
    """LangGraph-compatible node wrapper."""
    updated = run(state)
    return {"final_answer": updated["final_answer"]}

