"""
PrivacySwarm Streamlit Dashboard
Run: streamlit run ui/dashboard.py
"""
import sys
import pathlib
import json
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(
    page_title="PrivacySwarm",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("# 🔒 PrivacySwarm")
    st.markdown("*Local Privacy-Preserving Multi-Agent AI*")
    st.divider()

    page = st.radio(
        "Navigate",
        ["🔒 Privacy Pipeline", "📊 Evaluation Dashboard", "📋 Audit Log"],
        index=0,
    )
    st.divider()

    # Groq API key
    api_key = st.text_input(
        "Groq API Key (for cloud routing)",
        type="password",
        value=st.session_state.get("groq_key", ""),
        help="Get a free key at console.groq.com",
    )
    if api_key:
        st.session_state["groq_key"] = api_key
        import os; os.environ["GROQ_API_KEY"] = api_key

    # Ollama status
    st.divider()
    st.markdown("**System Status**")
    try:
        import httpx
        r = httpx.get("http://localhost:11434/api/tags", timeout=2)
        st.success("🟢 Ollama: Online")
    except Exception:
        st.error("🔴 Ollama: Offline")
        st.caption("Install from ollama.com and run: `ollama pull llama3.2:1b`")

    if api_key:
        st.success("🟢 Groq API: Configured")
    else:
        st.warning("🟡 Groq API: Not set")

    st.divider()
    st.caption("FAST-NUCES · AI-A · 2026")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Privacy Pipeline
# ══════════════════════════════════════════════════════════════════════════════

if page == "🔒 Privacy Pipeline":
    st.title("🔒 PrivacySwarm — Privacy Pipeline")
    st.markdown(
        "Enter sensitive text below. PrivacySwarm will **redact PII locally**, "
        "route the sanitized text intelligently, and restore names in the final answer."
    )

    EXAMPLE = (
        "Patient: Hassan Ali Raza\nCNIC: 35202-1234567-9\nContact: 0321-4567890\n"
        "MRN: MRN-556789\nDiagnosis: Type 2 Diabetes\nAttending: Dr. Fatima Khan\n"
        "Hospital: Shaukat Khanum Memorial Cancer Hospital\n\n"
        "Patient presented with elevated blood glucose levels. "
        "Prescribed Metformin 500mg twice daily. Follow-up in 4 weeks."
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        raw_text = st.text_area("📥 Input Document", value=EXAMPLE, height=200)
    with col2:
        task = st.text_input("📝 Task", value="Summarize this medical record.")
        run_btn = st.button("🚀 Run PrivacySwarm", type="primary", use_container_width=True)
        st.markdown("---")
        st.info("**Pipeline flow:**\n\n"
                "1. Symbolic Rule Engine\n"
                "2. Neural Redactor\n"
                "3. Symbolic Validator\n"
                "4. Hybrid Router\n"
                "5. Local Swarm OR Cloud\n"
                "6. Hallucination Detector\n"
                "7. Re-Inserter")

    if run_btn:
        with st.spinner("Running PrivacySwarm privacy pipeline..."):
            try:
                from pipeline.graph import run_pipeline
                t0    = time.time()
                state = run_pipeline(raw_text, task)
                elapsed = time.time() - t0
            except Exception as e:
                st.error(f"Pipeline error: {e}")
                st.stop()

        st.success(f"✅ Pipeline complete in {elapsed:.2f}s")

        # Metrics row
        pii_total = sum(state.get("pii_counts", {}).values())
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("🔍 PII Found",    pii_total)
        m2.metric("🛡️ Routing",      state.get("routing_decision", "—").upper())
        m3.metric("⏱️ Latency",       f"{elapsed:.2f}s")
        m4.metric("💬 Debate Rounds", state.get("debate_rounds", 0))
        m5.metric("🚨 Hallucination", "Yes" if state.get("hallucination_detected") else "No")

        st.divider()
        rc1, rc2 = st.columns(2)
        with rc1:
            st.markdown("**📄 Sanitized Text (sent to AI)**")
            sanitized = state.get("sanitized_text", "")
            st.code(sanitized, language="text")
        with rc2:
            st.markdown("**✅ Final Answer (names restored)**")
            st.markdown(state.get("final_answer", "*(no answer generated)*"))

        # Pipeline Details
        with st.expander("🔎 Pipeline Details"):
            st.markdown("**PII Token Map**")
            pii_map = state.get("pii_token_map", {})
            if pii_map:
                rows = [{"Real PII": k, "Token": v} for k, v in pii_map.items()]
                st.table(rows)
            else:
                st.info("No PII detected.")

            st.markdown("**Routing Decision**")
            st.write(f"Decision: `{state.get('routing_decision', '—')}`  "
                     f"Stage: `{state.get('routing_stage', '—')}`")
            st.write(f"Reason: {state.get('routing_reason', '—')}")

            if state.get("hallucination_detected"):
                st.warning(f"⚠️ Hallucination detected: {state.get('hallucination_reason')}")

            errs = state.get("errors", [])
            if errs:
                st.markdown("**Errors / Warnings**")
                for e in errs:
                    st.caption(f"• {e}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — Evaluation Dashboard
# ══════════════════════════════════════════════════════════════════════════════

elif page == "📊 Evaluation Dashboard":
    st.title("📊 Evaluation Dashboard")
    st.markdown("Run the evaluation suite on the synthetic dataset to measure all 6 metrics.")

    col1, col2 = st.columns(2)
    with col1:
        n_docs = st.slider("Number of documents to evaluate", 5, 100, 20, step=5)
    with col2:
        run_eval = st.button("▶️ Run Evaluation (PrivacySwarm)", type="primary")

    if run_eval:
        with st.spinner(f"Evaluating {n_docs} documents... this may take a while."):
            try:
                from evaluation.evaluator import run_full_evaluation, save_results
                results = run_full_evaluation(n_docs=n_docs, baseline_mode=False)
                st.session_state["eval_results"] = results
                save_results(results)
            except Exception as e:
                st.error(f"Evaluation error: {e}")

    if "eval_results" in st.session_state:
        r = st.session_state["eval_results"]

        st.success(f"✅ Evaluation complete — {r['n_valid']} documents processed")
        st.divider()

        # Metrics cards
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("🔒 PII Leakage",       f"{r['avg_pii_leakage_rate']:.1f}%",   delta=f"-{100-r['avg_pii_leakage_rate']:.0f}%")
        c2.metric("🎯 PII Recall",         f"{r['avg_pii_detection_recall']:.1f}%")
        c3.metric("📋 Factual Retention",  f"{r['avg_factual_retention']:.1f}%")
        c4.metric("⏱️ Avg Latency",         f"{r['avg_latency_seconds']:.2f}s")
        c5.metric("💰 Cloud Calls",         f"{r['routing_breakdown']['cloud']}/{r['n_valid']}")
        c6.metric("🚨 Hallucination Rate",  f"{r['hallucination_rate']:.1f}%")

        st.divider()
        st.markdown("**Per-Document Results**")
        import pandas as pd
        df = pd.DataFrame([d for d in r["per_doc_results"] if "error" not in d])
        if not df.empty:
            st.dataframe(df, use_container_width=True)

        # Charts
        try:
            from evaluation.visualize import (
                plot_routing_breakdown, plot_hallucination_detection,
                plot_pii_leakage_comparison, plot_detection_recall_by_method
            )
            st.divider()
            ch1, ch2 = st.columns(2)
            with ch1:
                fig = plot_routing_breakdown(r, save=False)
                st.pyplot(fig)
            with ch2:
                fig = plot_hallucination_detection(r, save=False)
                st.pyplot(fig)

            fig2 = plot_detection_recall_by_method(72.0, 68.0, r["avg_pii_detection_recall"], save=False)
            st.pyplot(fig2)
        except Exception as e:
            st.warning(f"Charts unavailable: {e}")

        # Download
        st.download_button(
            "⬇️ Download Results JSON",
            data=json.dumps(r, indent=2),
            file_name="privacyswarm_results.json",
            mime="application/json",
        )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — Audit Log
# ══════════════════════════════════════════════════════════════════════════════

elif page == "📋 Audit Log":
    st.title("📋 Audit Log")
    st.markdown("Tamper-evident record of every pipeline run.")

    try:
        from audit.audit_log import get_recent_runs, get_summary_stats
        import pandas as pd

        stats = get_summary_stats()
        if stats.get("total_runs", 0) == 0:
            st.info("No runs logged yet. Run the pipeline to see logs here.")
        else:
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Total Runs",   stats["total_runs"])
            s2.metric("Successful",   stats["successful_runs"])
            s3.metric("Avg PII Found", f"{stats['avg_pii_found']:.1f}")
            s4.metric("Avg Latency",  f"{stats['avg_latency']:.2f}s")

            st.divider()
            filter_opt = st.selectbox("Filter by routing", ["All", "local", "cloud"])
            runs = get_recent_runs(50)
            if filter_opt != "All":
                runs = [r for r in runs if r.get("routing_decision") == filter_opt]

            if runs:
                df = pd.DataFrame(runs)
                cols = ["run_id", "timestamp", "routing_decision", "pii_found_total",
                        "response_source", "hallucination_detected", "latency_seconds", "success"]
                st.dataframe(df[[c for c in cols if c in df.columns]], use_container_width=True)
            else:
                st.info("No runs match the filter.")

    except Exception as e:
        st.error(f"Audit log error: {e}")

