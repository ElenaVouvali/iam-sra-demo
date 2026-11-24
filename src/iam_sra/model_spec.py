"""Small shared model specification, also shipped with inference-only helpers."""
import json
import os
from pathlib import Path
import re


def thinking_enabled():
    value=os.getenv('IAM_MODEL_THINKING','0')
    if value not in {'0','1'}:raise ValueError('IAM_MODEL_THINKING must be 0 or 1.')
    return value=='1'


def context_tokens():
    return 8192 if thinking_enabled() else 4096


def reasoning_tokens():
    value=int(os.getenv('IAM_MODEL_REASONING_TOKENS','1536'))
    if not 512<=value<=4096:raise ValueError('IAM_MODEL_REASONING_TOKENS must be 512–4096.')
    return value if thinking_enabled() else 0


def model_variant(value=None):
    value = value if value is not None else os.getenv('IAM_MODEL_VARIANT', 'fp16')
    if value not in {'fp16', 'awq'}:
        raise ValueError('IAM_MODEL_VARIANT must be fp16 or awq.')
    return value


def load_model(root, variant=None):
    variant = model_variant(variant)
    name = 'model-awq.json' if variant == 'awq' else 'model.json'
    value = json.loads((Path(root) / 'configs' / name).read_text())
    if not re.fullmatch(r'[a-f0-9]{40}', value.get('revision', '')):
        raise ValueError('The model must have an exact revision pin.')
    if variant == 'awq' and (value.get('model') != 'Qwen/Qwen3-8B-AWQ'
            or value.get('quantization') != 'awq_marlin' or value.get('weight_bits') != 4
            or value.get('cpu_offload_gb') != 0):
        raise ValueError('The A2 fast model requires the pinned 4-bit AWQ specification and zero offload.')
    return value


def snapshot_path(root, spec):
    return (Path(root) / '.runtime/huggingface/hub' /
            ('models--' + spec['model'].replace('/', '--')) / 'snapshots' / spec['revision'])


def validate_awq_snapshot(path):
    """Fail before GPU allocation for missing shards or a wrong quantization."""
    path = Path(path)
    config = json.loads((path / 'config.json').read_text())
    quant = config.get('quantization_config', {})
    if config.get('model_type') != 'qwen3' or quant.get('bits') != 4 or quant.get('quant_method') != 'awq':
        raise ValueError('The cached fast snapshot is not a 4-bit AWQ Qwen3 model.')
    index = json.loads((path / 'model.safetensors.index.json').read_text())
    shards = set(index.get('weight_map', {}).values())
    if not shards or any(Path(s).name != s or not s.endswith('.safetensors') for s in shards):
        raise ValueError('Invalid AWQ weight index.')
    for name in [*shards, 'tokenizer.json', 'tokenizer_config.json']:
        if not (path / name).is_file() or (path / name).stat().st_size == 0:
            raise ValueError('Incomplete AWQ snapshot; run scripts/download-model.py with IAM_MODEL_VARIANT=awq.')
    return path
