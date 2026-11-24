"""Download the selected pinned checkpoint additively; never replace old weights."""
from pathlib import Path
import os
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
os.environ['HF_HOME']=str(ROOT/'.runtime/huggingface')
try:
    from iam_sra.model_spec import load_model, model_variant, snapshot_path, validate_awq_snapshot
except ModuleNotFoundError:
    from model_spec import load_model, model_variant, snapshot_path, validate_awq_snapshot  # Inference-only upload; no application package.
from huggingface_hub import snapshot_download

spec=load_model(ROOT)
if model_variant()=='awq':
    try:
        ready=validate_awq_snapshot(snapshot_path(ROOT,spec))
    except (OSError,ValueError,KeyError):
        if shutil.disk_usage(ROOT).free < 16*1024**3:
            raise SystemExit('AWQ preparation requires 16 GiB free for the additive download and runtime headroom. No files were deleted.')
    else:
        print('Pinned AWQ snapshot is already complete:',ready)
        raise SystemExit(0)
print('Preparing pinned model:',spec['model'],spec['revision'],flush=True)
path=Path(snapshot_download(spec['model'],revision=spec['revision'],
    allow_patterns=['*.json','*.safetensors','*.jinja','*.txt','LICENSE'],max_workers=2))
if model_variant()=='awq':validate_awq_snapshot(path)
print(path)
