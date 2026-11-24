import json
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
def config(name):
    if name == 'model':
        from .model_spec import load_model
        return load_model(ROOT)
    return json.loads((ROOT / "configs" / f"{name}.json").read_text())
REGISTRY = config("concerns")
CONCERNS = {c["id"]: c for c in REGISTRY["concerns"]}
SCENARIO = config("scenario")
MODEL = config("model")["model"]
BASE_URL = os.getenv("IAM_BASE_URL", "http://127.0.0.1:8000")
MAX_INPUT_BYTES = 4000
from .model_spec import context_tokens
CONTEXT_TOKENS = context_tokens()
