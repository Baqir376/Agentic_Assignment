"""
Audit Log Engine — SQLite-based tamper-evident record of every pipeline run.
"""
import sys
import sqlite3
import json
import uuid
import time
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from config import AUDIT_DB_PATH
from pipeline.state import PipelineState

# Ensure the audit directory exists
AUDIT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS audit_log (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id              TEXT NOT NULL,
    timestamp           TEXT NOT NULL,
    category            TEXT,
    pii_found_total     INTEGER DEFAULT 0,
    pii_by_type         TEXT,
    routing_decision    TEXT,
    routing_stage       TEXT,
    sensitivity_flagged INTEGER DEFAULT 0,
    response_source     TEXT,
    hallucination_detected INTEGER DEFAULT 0,
    hallucination_retries  INTEGER DEFAULT 0,
    validation_attempts    INTEGER DEFAULT 0,
    debate_rounds          INTEGER DEFAULT 0,
    tokens_in_pii_map      INTEGER DEFAULT 0,
    errors                 TEXT,
    latency_seconds        REAL DEFAULT 0.0,
    success                INTEGER DEFAULT 0
);
"""


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(AUDIT_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the database and audit_log table if they don't exist."""
    with _get_conn() as conn:
        conn.execute(CREATE_TABLE_SQL)
        conn.commit()


def log_run(state: PipelineState) -> str:
    """
    Insert one audit record from the final pipeline state.
    Returns the run_id (UUID string).
    """
    run_id  = str(uuid.uuid4())
    ts      = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    latency = time.time() - state.get("start_time", time.time())

    pii_counts = state.get("pii_counts", {})
    pii_total  = sum(pii_counts.values())

    row = {
        "run_id":               run_id,
        "timestamp":            ts,
        "category":             state.get("audit_entry", {}).get("category", "unknown"),
        "pii_found_total":      pii_total,
        "pii_by_type":          json.dumps(pii_counts),
        "routing_decision":     state.get("routing_decision", ""),
        "routing_stage":        state.get("routing_stage", ""),
        "sensitivity_flagged":  int(state.get("sensitivity_flagged", False)),
        "response_source":      state.get("response_source", ""),
        "hallucination_detected": int(state.get("hallucination_detected", False)),
        "hallucination_retries":  state.get("hallucination_retry_count", 0),
        "validation_attempts":    state.get("validation_attempts", 0),
        "debate_rounds":          state.get("debate_rounds", 0),
        "tokens_in_pii_map":      len(state.get("reverse_map", {})),
        "errors":                 json.dumps(state.get("errors", [])),
        "latency_seconds":        round(latency, 3),
        "success":                1 if state.get("final_answer", "") else 0,
    }

    sql = """INSERT INTO audit_log
             (run_id, timestamp, category, pii_found_total, pii_by_type,
              routing_decision, routing_stage, sensitivity_flagged,
              response_source, hallucination_detected, hallucination_retries,
              validation_attempts, debate_rounds, tokens_in_pii_map,
              errors, latency_seconds, success)
             VALUES
             (:run_id, :timestamp, :category, :pii_found_total, :pii_by_type,
              :routing_decision, :routing_stage, :sensitivity_flagged,
              :response_source, :hallucination_detected, :hallucination_retries,
              :validation_attempts, :debate_rounds, :tokens_in_pii_map,
              :errors, :latency_seconds, :success)"""

    with _get_conn() as conn:
        conn.execute(sql, row)
        conn.commit()

    return run_id


def get_summary_stats() -> dict:
    """Return aggregate statistics across all logged runs."""
    with _get_conn() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*)                        AS total_runs,
                SUM(success)                    AS successful_runs,
                AVG(pii_found_total)            AS avg_pii_found,
                AVG(latency_seconds)            AS avg_latency,
                SUM(CASE WHEN routing_decision='local' THEN 1 ELSE 0 END) AS local_count,
                SUM(CASE WHEN routing_decision='cloud' THEN 1 ELSE 0 END) AS cloud_count,
                AVG(hallucination_detected)     AS hallucination_rate,
                AVG(validation_attempts)        AS avg_validation_attempts
            FROM audit_log
        """).fetchone()

    if not row or row["total_runs"] == 0:
        return {"total_runs": 0}

    return {
        "total_runs":              row["total_runs"],
        "successful_runs":         row["successful_runs"],
        "avg_pii_found":           round(row["avg_pii_found"] or 0, 2),
        "avg_latency":             round(row["avg_latency"] or 0, 3),
        "routing_breakdown":       {"local": row["local_count"], "cloud": row["cloud_count"]},
        "hallucination_rate":      round((row["hallucination_rate"] or 0) * 100, 1),
        "avg_validation_attempts": round(row["avg_validation_attempts"] or 0, 2),
    }


def get_recent_runs(limit: int = 20) -> list[dict]:
    """Return the most recent N runs as a list of dicts."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# ── LangGraph node ────────────────────────────────────────────────────────────

def audit_logger_node(state: PipelineState) -> dict:
    """LangGraph-compatible node: log this run and return audit entry."""
    run_id = log_run(state)
    entry  = {**state.get("audit_entry", {}), "run_id": run_id, "logged_at": time.time()}
    return {"audit_entry": entry}


# Initialize DB on import
init_db()

