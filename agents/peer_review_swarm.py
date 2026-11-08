"""
Agent 3 — Local Peer Review Swarm
Two SLMs debate to produce a high-quality local answer (no cloud call).
SLM-A drafts → SLM-B critiques → SLM-A revises → repeat up to MAX_DEBATE_ROUNDS.
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from config import LOCAL_MODEL_NAME, OLLAMA_BASE_URL, MAX_DEBATE_ROUNDS
from pipeline.state import PipelineState

DRAFTER_SYSTEM = """You are a helpful, precise AI assistant.
Answer the given task using ONLY the information in the provided context.
Preserve any [TYPE_N] tokens EXACTLY as they appear — never replace or omit them.
Do NOT invent facts not present in the context.
Be concise and direct."""

CRITIC_SYSTEM = """You are a strict fact-checking reviewer.
You will receive: (1) a context document, (2) a task, and (3) a draft response.
Your job: check the response for hallucinations, missing key facts, or logical errors.
Preserve [TYPE_N] tokens exactly as given.

If the response is acceptable: reply with EXACTLY the word ACCEPT (nothing else).
If there are issues: reply with REVISE: followed by specific correction instructions."""


def _call_llm(messages: list, errors: list) -> str:
    """Call the local Ollama SLM. Returns response text or empty string on error."""
    try:
        from langchain_ollama import ChatOllama
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = ChatOllama(model=LOCAL_MODEL_NAME, base_url=OLLAMA_BASE_URL, temperature=0.1)
        resp = llm.invoke(messages)
        return resp.content
    except Exception as e:
        errors.append(f"[PeerReviewSwarm] Ollama error: {e}")
        return ""


def run(state: PipelineState) -> PipelineState:
    """Run the two-agent debate loop and produce a final local response."""
    from langchain_core.messages import HumanMessage, SystemMessage

    context = state.get("sanitized_text", "")
    task    = state.get("task_description", "Summarize this document.")
    errors  = list(state.get("errors", []))

    draft   = ""
    rounds  = 0

    for round_num in range(MAX_DEBATE_ROUNDS):
        rounds += 1

        # ── Drafter generates / revises ───────────────────────────────────────
        if draft == "":
            drafter_user = (
                f"Context:\n{context}\n\n"
                f"Task: {task}\n\n"
                f"Write your response now:"
            )
        else:
            drafter_user = (
                f"Context:\n{context}\n\n"
                f"Task: {task}\n\n"
                f"Your previous draft:\n{draft}\n\n"
                f"Reviewer's critique:\n{critique}\n\n"
                f"Revise your response based on the critique:"
            )

        draft = _call_llm(
            [SystemMessage(content=DRAFTER_SYSTEM), HumanMessage(content=drafter_user)],
            errors,
        )
        if not draft:
            # An unavailable model is not a generated answer.
            draft = ""
            break

        # ── Critic evaluates ──────────────────────────────────────────────────
        critic_user = (
            f"Context:\n{context}\n\n"
            f"Task: {task}\n\n"
            f"Draft response to evaluate:\n{draft}"
        )
        critique = _call_llm(
            [SystemMessage(content=CRITIC_SYSTEM), HumanMessage(content=critic_user)],
            errors,
        )

        if not critique or critique.strip().upper().startswith("ACCEPT"):
            break  # Consensus reached

    state["raw_response"]    = draft
    state["response_source"] = "local_swarm"
    state["debate_rounds"]   = rounds
    state["errors"]          = errors
    return state


def peer_review_swarm_node(state: PipelineState) -> dict:
    """LangGraph-compatible node wrapper."""
    updated = run(state)
    return {
        "raw_response":    updated["raw_response"],
        "response_source": updated["response_source"],
        "debate_rounds":   updated["debate_rounds"],
        "errors":          updated["errors"],
    }

