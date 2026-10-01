import json
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
def config(name):
    return json.loads((ROOT / "configs" / f"{name}.json").read_text())
REGISTRY = config("concerns")
CONCERNS = {c["id"]: c for c in REGISTRY["concerns"]}
SCENARIO = config("scenario")
POLICY = config("scoring")
QUESTIONS = config("validation")["questions"]
MODEL = "Qwen/Qwen3-8B"
BASE_URL = os.getenv("IAM_BASE_URL", "http://127.0.0.1:8000")
MAX_INPUT_BYTES = 4000
MAX_OUTPUT_TOKENS = 1600
CONTEXT_TOKENS = 4096
