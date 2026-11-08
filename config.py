# ============================================================
# PrivacySwarm Configuration
# ============================================================
import os
import pathlib
from dotenv import load_dotenv

BASE_DIR = pathlib.Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

# --- API Keys ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# --- Local SLM (Ollama) ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Smart auto-detect model: prefer qwen2.5:3b or first available installed model
def _get_default_local_model():
    env_model = os.getenv("LOCAL_MODEL")
    if env_model:
        return env_model
    try:
        import httpx
        r = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=1.0)
        if r.status_code == 200:
            models = [m.get("name") for m in r.json().get("models", [])]
            for preferred in ["qwen2.5:3b", "qwen2.5-coder:3b", "llama3.2:1b", "gemma4:latest"]:
                for m in models:
                    if preferred in m:
                        return m
            if models:
                return models[0]
    except Exception:
        pass
    return "qwen2.5:3b"

LOCAL_MODEL_NAME = _get_default_local_model()
LOCAL_DEBATE_MODEL = os.getenv("LOCAL_DEBATE_MODEL", LOCAL_MODEL_NAME)

# --- Cloud Model (Groq — free tier) ---
CLOUD_MODEL_NAME = os.getenv("CLOUD_MODEL", "llama-3.1-8b-instant")

# --- Router Thresholds ---
COMPLEXITY_THRESHOLD = 0.6        # Neural score above this → route to cloud
SENSITIVITY_THRESHOLD = 0.8      # Sensitivity score above this → local ONLY, never cloud
MIN_WORD_COUNT_FOR_LOCAL = 50    # Tasks under 50 words go local if simple

# --- Validator Settings ---
MAX_VALIDATION_ATTEMPTS = 3      # How many times to retry redaction if validator fails

# --- Hallucination Detector Settings ---
MAX_HALLUCINATION_RETRIES = 2    # How many times to retry if hallucination found

# --- Peer Review Swarm Settings ---
MAX_DEBATE_ROUNDS = 3            # Maximum back-and-forth debate rounds

# --- Paths ---
import pathlib
BASE_DIR = pathlib.Path(__file__).parent
ONTOLOGY_DIR = BASE_DIR / "data" / "ontology"
SYNTHETIC_DIR = BASE_DIR / "data" / "synthetic"
AUDIT_DB_PATH = BASE_DIR / "audit" / "audit.db"

# --- PII Token Prefixes ---
PII_TYPES = {
    "PERSON":     "PERSON",
    "PHONE":      "PHONE",
    "EMAIL":      "EMAIL",
    "CNIC":       "CNIC",
    "DATE":       "DATE",
    "LOCATION":   "LOC",
    "HOSPITAL":   "HOSP",
    "MEDICAL_ID": "MED_ID",
    "OTHER":      "OTHER",
}

# --- Symbolic Router Rules ---
# Keywords that force COMPLEX routing (→ cloud)
COMPLEX_KEYWORDS = [
    "diagnose", "diagnosis", "treatment plan", "prognosis", "prescription",
    "legal interpretation", "contract analysis", "liability", "criminal",
    "interpret", "analyze in depth", "explain the law", "legal advice",
    "differential diagnosis", "drug interaction",
]

# Keywords that force SIMPLE routing (→ local)
SIMPLE_KEYWORDS = [
    "summarize", "summary", "list", "bullet points", "reformat",
    "translate", "count", "how many", "extract", "highlight",
]

# High-sensitivity topic keywords → never send to cloud regardless
SENSITIVE_TOPICS = [
    "hiv", "aids", "mental health", "psychiatric", "substance abuse",
    "domestic violence", "suicide", "sexual", "abortion",
    "immigration status", "undocumented", "salary", "bank account",
]

