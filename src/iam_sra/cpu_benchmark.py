"""CPU-only benchmark adapter; preserves the screened transport and validators."""
import os
import time
from .baseline_client import BaselineClient
from .assessment import AssessmentError
from .settings import ROOT, config


class CPURuntime:
    def __init__(self, threads=4, generation_seconds=300):
        if not 1 <= threads <= 16 or not 10 <= generation_seconds <= 3600:
            raise ValueError('CPU threads must be 1–16; generation seconds must be 10–3600.')
        self.threads = threads
        self.generation_seconds = generation_seconds
        self.ready = False
        self.load_seconds = None

    def load(self):
        if self.ready:
            return
        # No GPU enumeration or allocation, even with a CUDA-enabled torch wheel.
        os.environ['CUDA_VISIBLE_DEVICES'] = ''
        os.environ['HF_HUB_OFFLINE'] = '1'
        os.environ['TOKENIZERS_PARALLELISM'] = 'false'
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM
        import xgrammar as xgr
        started = time.monotonic()
        snapshot = ROOT / '.runtime/huggingface/hub/models--Qwen--Qwen3-8B/snapshots' / config('model')['revision']
        if not (snapshot / 'config.json').exists():
            raise AssessmentError('Pinned local model snapshot is missing.', code='transport')
        torch.set_num_threads(self.threads)
        self.tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True)
        self.model = AutoModelForCausalLM.from_pretrained(snapshot, local_files_only=True,
            torch_dtype=torch.float32, attn_implementation='sdpa').eval()
        if any(p.device.type != 'cpu' for p in self.model.parameters()):
            raise RuntimeError('CPU benchmark refuses a non-CPU model.')
        info = xgr.TokenizerInfo.from_huggingface(self.tokenizer, vocab_size=self.model.config.vocab_size)
        self.compiler = xgr.GrammarCompiler(info)
        self.load_seconds = round(time.monotonic() - started, 4)
        self.ready = True

    def metadata(self):
        from importlib.metadata import PackageNotFoundError, version
        libraries = {}
        for name in ('torch', 'transformers', 'xgrammar'):
            try:
                libraries[name] = version(name)
            except PackageNotFoundError:
                libraries[name] = None
        return {'device': 'cpu', 'backend': 'transformers_xgrammar_cpu', 'dtype': 'float32',
            'threads': self.threads, 'seed': 42, 'generation_timeout_seconds': self.generation_seconds,
            'model_load_seconds': self.load_seconds, 'model_loaded': self.ready,
            'libraries': libraries,
            'gpu_timing_comparable': False}


class CPUBaselineClient(BaselineClient):
    def __init__(self, runtime):
        super().__init__(base_url='cpu-local')
        self.runtime = runtime

    def _start(self):
        super()._start()
        self._deadline = time.monotonic() + 4 * self.runtime.generation_seconds + 600
        self.last_settings.update({'backend': 'transformers_xgrammar_cpu',
            'stage_deadline_seconds': 4 * self.runtime.generation_seconds + 600,
            'expected_deployment': self.runtime.metadata()})

    def _post_json(self, client, path, payload, stage, phase):
        self.runtime.load()
        runtime = self.runtime
        self.last_settings['expected_deployment'] = runtime.metadata()
        self.last_metrics['tokenize_calls' if phase == 'tokenization' else 'generation_calls'] += 1
        ids = runtime.tokenizer.apply_chat_template(payload['messages'], tokenize=True,
            add_generation_prompt=True, enable_thinking=False, return_tensors='pt')
        if path == '/tokenize':
            return {'count': ids.shape[-1]}
        if path != '/v1/chat/completions':
            raise ValueError('Unsupported CPU benchmark operation')
        import torch
        from xgrammar.contrib.hf import LogitsProcessor
        # Match the existing no-flexible-whitespace deployment policy.
        grammar = runtime.compiler.compile_json_schema(payload['guided_json'], any_whitespace=False)
        started = time.monotonic()
        print(f'CPU generation started: {stage}, output limit {payload["max_tokens"]}', flush=True)
        torch.manual_seed(42)
        with torch.inference_mode():
            output = runtime.model.generate(input_ids=ids, attention_mask=torch.ones_like(ids),
                max_new_tokens=payload['max_tokens'], max_time=min(runtime.generation_seconds,
                    max(1, self._deadline - time.monotonic())),
                do_sample=True, temperature=payload['temperature'], top_p=payload['top_p'],
                top_k=0, logits_processor=[LogitsProcessor(grammar)],
                pad_token_id=runtime.tokenizer.eos_token_id)
        generated = output[0, ids.shape[-1]:]
        stop_ids = runtime.model.generation_config.eos_token_id
        stop_ids = stop_ids if isinstance(stop_ids, list) else [stop_ids]
        finished = len(generated) > 0 and int(generated[-1]) in stop_ids
        elapsed = round(time.monotonic() - started, 4)
        print(f'CPU generation finished: {stage}, {len(generated)} tokens, {elapsed} seconds, stopped={finished}', flush=True)
        self.last_diagnostics.append({'stage': stage, 'device': 'cpu',
            'generation_seconds': elapsed, 'output_tokens': len(generated)})
        return {'choices': [{'message': {'content': runtime.tokenizer.decode(generated, skip_special_tokens=True)},
            'finish_reason': 'stop' if finished else 'length'}]}
