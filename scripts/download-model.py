from pathlib import Path
import json
import os
ROOT=Path(__file__).resolve().parents[1]
os.environ["HF_HOME"]=str(ROOT/".runtime/huggingface")
from huggingface_hub import snapshot_download
model=json.loads((ROOT/"configs/model.json").read_text())
print(snapshot_download(model['model'],revision=model['revision'],allow_patterns=["*.json","*.safetensors","*.jinja","*.txt"],max_workers=2))
