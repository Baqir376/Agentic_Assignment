"""Quick audit DB stats check."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import warnings
warnings.filterwarnings("ignore")

from audit.audit_log import get_summary_stats, get_recent_runs
import json

print("=== Audit DB Stats ===")
print(json.dumps(get_summary_stats(), indent=2))
print()
print("=== Recent Runs ===")
runs = get_recent_runs(5)
for r in runs:
    rid = r["run_id"][:8]
    print(f"  {rid}... routing={r['routing_decision']} pii={r['pii_found_total']} latency={r['latency_seconds']}s success={r['success']}")

