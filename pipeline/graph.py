"""
PrivacySwarm LangGraph Pipeline — State Machine
Connects all agents into an end-to-end graph with conditional edges.
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from langgraph.graph import StateGraph, END
from pipeline.state import PipelineState, initial_state

from agents.symbolic_rule_engine import symbolic_rule_engine_node
from agents.symbolic_validator import symbolic_validator_node, validator_route
from agents.neural_redactor import neural_redactor_node
from agents.hybrid_router import hybrid_router_node, router_route
from agents.peer_review_swarm import peer_review_swarm_node
from agents.reinserter import cloud_processor_node, reinserter_node
from agents.hallucination_detector import hallucination_detector_node, hallucination_route
from audit.audit_log import audit_logger_node


def build_graph():
    """
    Build and compile the PrivacySwarm LangGraph pipeline.

    Flow:
        symbolic_rule_engine
            → neural_redactor
            → symbolic_validator
                ├─ retry  → neural_redactor
                └─ proceed → hybrid_router
                    ├─ local → peer_review_swarm
                    └─ cloud → cloud_processor
                        └─ hallucination_detector
                            ├─ pass         → reinserter
                            ├─ retry_local  → peer_review_swarm
                            └─ retry_cloud  → cloud_processor
                                → audit_logger → END
    """
    workflow = StateGraph(PipelineState)

    # Register all nodes
    workflow.add_node("symbolic_rule_engine",    symbolic_rule_engine_node)
    workflow.add_node("neural_redactor",         neural_redactor_node)
    workflow.add_node("symbolic_validator",      symbolic_validator_node)
    workflow.add_node("hybrid_router",           hybrid_router_node)
    workflow.add_node("peer_review_swarm",       peer_review_swarm_node)
    workflow.add_node("cloud_processor",         cloud_processor_node)
    workflow.add_node("hallucination_detector",  hallucination_detector_node)
    workflow.add_node("reinserter",              reinserter_node)
    workflow.add_node("audit_logger",            audit_logger_node)

    # Entry point
    workflow.set_entry_point("symbolic_rule_engine")

    # Fixed edges
    workflow.add_edge("symbolic_rule_engine", "neural_redactor")
    workflow.add_edge("neural_redactor",      "symbolic_validator")

    # Validator: retry redactor OR proceed to router
    workflow.add_conditional_edges(
        "symbolic_validator",
        validator_route,
        {"retry": "neural_redactor", "proceed": "hybrid_router", "blocked": "audit_logger"},
    )

    # Router: local swarm OR cloud
    workflow.add_conditional_edges(
        "hybrid_router",
        router_route,
        {"local": "peer_review_swarm", "cloud": "cloud_processor"},
    )

    # Both paths go to hallucination detector
    workflow.add_edge("peer_review_swarm", "hallucination_detector")
    workflow.add_edge("cloud_processor",   "hallucination_detector")

    # Hallucination: pass / retry local / retry cloud
    workflow.add_conditional_edges(
        "hallucination_detector",
        hallucination_route,
        {
            "pass":         "reinserter",
            "retry_local":  "peer_review_swarm",
            "retry_cloud":  "cloud_processor",
        },
    )

    # Final steps
    workflow.add_edge("reinserter",    "audit_logger")
    workflow.add_edge("audit_logger",  END)

    return workflow.compile()


def run_pipeline(raw_text: str, task_description: str = "Summarize this document.") -> dict:
    """
    Convenience wrapper: build graph, create initial state, run, return final state.
    """
    graph = build_graph()
    state = initial_state(raw_text, task_description)
    return graph.invoke(state)

