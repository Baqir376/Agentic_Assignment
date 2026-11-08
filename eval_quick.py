"""Quick 5-doc evaluation run."""
import sys, pathlib, warnings
sys.path.insert(0, str(pathlib.Path(__file__).parent))
warnings.filterwarnings("ignore")

from evaluation.evaluator import run_full_evaluation, save_results

results = run_full_evaluation(n_docs=5)
path = save_results(results)
print(f"\nResults saved -> {path}")
print(f"Run charts: python evaluation/visualize.py {path}")

