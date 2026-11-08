#!/usr/bin/env python3
"""
PrivacySwarm — CLI Entry Point
Usage:
  python main.py --text "Patient John Doe..." --task "Summarize"
  python main.py --file document.txt --task "Diagnose"
  python main.py --evaluate --n 20
  python main.py --ui
  python main.py --generate-data
  python main.py --check
"""
import sys
import argparse
import pathlib
import time
import json

sys.path.insert(0, str(pathlib.Path(__file__).parent))


def print_banner():
    print("""
╔══════════════════════════════════════════════════╗
║          🔒  P R I V A C Y S W A R M  🔒        ║
║   Local Privacy-Preserving Multi-Agent AI        ║
║   FAST-NUCES · AI-A · 2026                       ║
╚══════════════════════════════════════════════════╝
""")


def run_health_check():
    print("Running health check...\n")
    ok = True

    # 1. Import all agents
    try:
        from agents.symbolic_rule_engine import symbolic_rule_engine_node
        from agents.symbolic_validator import symbolic_validator_node
        from agents.neural_redactor import neural_redactor_node
        from agents.hybrid_router import hybrid_router_node
        from agents.peer_review_swarm import peer_review_swarm_node
        from agents.reinserter import cloud_processor_node, reinserter_node
        from agents.hallucination_detector import hallucination_detector_node
        from audit.audit_log import audit_logger_node
        print("  ✅ All agent modules imported successfully")
    except Exception as e:
        print(f"  ❌ Agent import error: {e}")
        ok = False

    # 2. Check Ollama
    try:
        import httpx
        r = httpx.get("http://localhost:11434/api/tags", timeout=3)
        models = [m["name"] for m in r.json().get("models", [])]
        print(f"  ✅ Ollama online. Available models: {models or '(none pulled yet)'}")
        if not any("llama" in m or "qwen" in m for m in models):
            print("  ⚠️  No suitable model found. Run: ollama pull llama3.2:1b")
    except Exception:
        print("  ⚠️  Ollama not running. Local SLM agents will be skipped.")
        print("       Install from: https://ollama.com and run: ollama pull llama3.2:1b")

    # 3. Check Groq key
    from config import GROQ_API_KEY
    if GROQ_API_KEY and len(GROQ_API_KEY) > 10:
        print("  ✅ GROQ_API_KEY is set")
    else:
        print("  ⚠️  GROQ_API_KEY not set. Cloud routing path disabled.")
        print("       Get a free key at: https://console.groq.com")

    # 4. Check dataset
    from config import SYNTHETIC_DIR
    ds_path = SYNTHETIC_DIR / "dataset.json"
    if ds_path.exists():
        with open(ds_path) as f:
            n = len(json.load(f))
        print(f"  ✅ Dataset found: {n} documents at {ds_path}")
    else:
        print(f"  ⚠️  Dataset missing. Run: python data/generate_dataset.py")

    print()
    if ok:
        print("  System ready. Run with --ui or --text to start.\n")
    else:
        print("  Some issues found. See above.\n")


def process_text(raw_text: str, task: str):
    from pipeline.graph import run_pipeline
    print(f"\n  Processing {len(raw_text)} characters...\n")

    t0    = time.time()
    state = run_pipeline(raw_text, task)
    elapsed = time.time() - t0

    pii_total = sum(state.get("pii_counts", {}).values())
    pii_detail = ", ".join(f"{k}:{v}" for k, v in state.get("pii_counts", {}).items())

    print("═" * 56)
    print("           PrivacySwarm Results")
    print("═" * 56)
    print(f"  📥 Input  : {raw_text[:80].strip()}...")
    print(f"  🔍 PII    : {pii_total} entities ({pii_detail})")
    print(f"  🛡️  Route  : {state.get('routing_decision','?').upper()} "
          f"({state.get('routing_stage','?')} stage)")
    print(f"  ⏱️  Latency: {elapsed:.2f}s")
    if state.get("hallucination_detected"):
        print(f"  🚨 Hallucination flagged: {state.get('hallucination_reason','')[:60]}")
    if state.get("errors"):
        print(f"  ⚠️  Errors : {len(state['errors'])} (use --verbose to see)")
    print()
    print("  📤 Final Answer:")
    print("─" * 56)
    print(state.get("final_answer", "(no answer generated)"))
    print("═" * 56)
    print()


def main():
    print_banner()

    parser = argparse.ArgumentParser(
        description="PrivacySwarm — Local Privacy-Preserving Multi-Agent AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--text",          help="Raw input text to process")
    parser.add_argument("--file",          help="Path to input text file")
    parser.add_argument("--task",          default="Summarize this document.", help="Task description")
    parser.add_argument("--evaluate",      action="store_true", help="Run evaluation suite")
    parser.add_argument("--n",             type=int, default=20, help="Docs to evaluate (default: 20)")
    parser.add_argument("--ui",            action="store_true", help="Launch Streamlit dashboard")
    parser.add_argument("--web",           action="store_true", help="Launch Modern React/Tailwind Dashboard on :8000")
    parser.add_argument("--generate-data", action="store_true", help="Generate synthetic dataset")
    parser.add_argument("--check",         action="store_true", help="Run health check")
    args = parser.parse_args()

    if args.check:
        run_health_check()

    elif args.generate_data:
        print("  Generating synthetic dataset...\n")
        import subprocess
        subprocess.run([sys.executable, "data/generate_dataset.py"])

    elif args.ui:
        print("  Launching Streamlit dashboard...\n")
        import subprocess
        subprocess.run([sys.executable, "-m", "streamlit", "run", "ui/dashboard.py"])

    elif args.web:
        import server
        server.start_server(8000)

    elif args.evaluate:
        from evaluation.evaluator import run_full_evaluation, save_results
        results = run_full_evaluation(n_docs=args.n)
        path = save_results(results)
        print(f"\n  Results saved → {path}")
        print(f"  Generate charts: python evaluation/visualize.py {path}")

    elif args.text:
        process_text(args.text, args.task)

    elif args.file:
        p = pathlib.Path(args.file)
        if not p.exists():
            print(f"  ❌ File not found: {p}")
            sys.exit(1)
        process_text(p.read_text(encoding="utf-8"), args.task)

    else:
        parser.print_help()
        print("\n  Quick start:\n"
              '  python main.py --check\n'
              '  python main.py --generate-data\n'
              '  python main.py --text "Patient John Doe, CNIC 35202-1234567-9..." '
              '--task "Summarize"\n'
              '  python main.py --ui\n')


if __name__ == "__main__":
    main()

