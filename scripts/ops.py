#!/usr/bin/env python3
"""Local processes only; process identity checked before any signal."""
import argparse
import importlib.metadata
import json
import math
import os
from pathlib import Path
import signal
import re
import socket
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
try:
    from iam_sra.model_spec import load_model, model_variant, snapshot_path, validate_awq_snapshot, thinking_enabled, context_tokens
except ModuleNotFoundError:
    from model_spec import load_model, model_variant, snapshot_path, validate_awq_snapshot, thinking_enabled, context_tokens  # Inference-only upload; no application package.
RUNTIME=ROOT/".runtime"
UUID=os.getenv("IAM_GPU_UUID", "")
PROFILE=os.getenv("IAM_GPU_PROFILE", "")
VPORT=int(os.getenv("IAM_VLLM_PORT","8000"))
UPORT=int(os.getenv("IAM_UI_PORT","8501"))
BASE_URL=os.getenv("IAM_BASE_URL",f"http://127.0.0.1:{VPORT}").rstrip("/")
def gpu_class(row):
    """Match NVIDIA product tokens, not e.g. A2000 when requesting an A2."""
    name,cap=row[2:4]
    for product,compute in [("v100s","7.0"),("v100","7.0"),("a30","8.0"),("a2","8.6")]:
        if re.search(r"(?<![A-Z0-9])"+product.upper()+r"(?![A-Z0-9])",name.upper()) and cap==compute:
            return product
    return None

def gpu():
    profile=None
    if PROFILE:
        profiles=json.loads((ROOT/"configs/gpu-profiles.json").read_text())["profiles"]
        if PROFILE not in profiles: raise RuntimeError("Unknown IAM_GPU_PROFILE: "+PROFILE)
        profile=profiles[PROFILE]
        if socket.gethostname().split(".")[0].lower()!=profile["host"]:
            raise RuntimeError(f"Profile {PROFILE} must run on {profile['host']}; use scripts/model-host.py")
    output=subprocess.check_output(["nvidia-smi","--query-gpu=index,uuid,name,compute_cap,memory.total,memory.used,driver_version","--format=csv,noheader,nounits"],text=True)
    rows=[list(map(str.strip,r.split(","))) for r in output.strip().splitlines()]
    selected=[r for r in rows if r[1]==UUID] if UUID else [r for r in rows
        if gpu_class(r) and (not profile or gpu_class(r)==profile["gpu"]) and float(r[5])<=2048]
    if len(selected)!=1:
        raise RuntimeError("Configured IAM_GPU_UUID is absent from this host; run scripts/diagnose-model.py" if UUID else
            "No unique idle supported GPU is available. Existing workloads are retained. Run scripts/diagnose-model.py; set IAM_GPU_UUID only for an available GPU.")
    row=selected[0]
    if not gpu_class(row):
        raise RuntimeError("Selected GPU must be a V100/V100S (7.0), A30 (8.0) or A2 (8.6); refusing launch")
    if profile and gpu_class(row)!=profile["gpu"]:
        raise RuntimeError("IAM_GPU_UUID does not match selected profile "+PROFILE)
    if float(row[5])>2048:
        raise RuntimeError(f"{row[2]} has an existing workload (>2 GiB); refusing to reserve GPU")
    print(output)
    return selected[0]

def cpu_offload(row):
    if model_variant() == 'awq':
        value=float(os.getenv("IAM_CPU_OFFLOAD_GB", "0"))
        if value != 0: raise RuntimeError("AWQ fast mode requires zero CPU offload")
        return 0.0
    # FP16 Qwen3-8B plus KV/cache overhead does not fit a 16 GB card.
    # Keep the same model/context; offload weights rather than quantize it.
    value=float(os.getenv("IAM_CPU_OFFLOAD_GB", "8" if float(row[4])<=18432 else "0"))
    if not math.isfinite(value) or not 0<=value<=16:
        raise RuntimeError("IAM_CPU_OFFLOAD_GB must be between 0 and 16")
    return value

def check_offload_memory(row):
    offload=cpu_offload(row)
    if offload:
        fields=dict(line.split(":",1) for line in Path("/proc/meminfo").read_text().splitlines())
        available=int(fields["MemAvailable"].split()[0])*1024/1024**3
        if available<offload+4:
            raise RuntimeError(f"CPU offloading needs at least {offload+4:g} GiB available host RAM")
        print(f"CPU weight offload: {offload:g} GiB; generation will be slower. Available host RAM: {available:.1f} GiB")

def complete_cached_snapshot():
    """Confirm the pinned FP16/AWQ files are already present and readable."""
    try:
        model=load_model(ROOT)
        snapshot=snapshot_path(ROOT,model)
        if model_variant()=='awq':
            validate_awq_snapshot(snapshot)
            return True
        config=json.loads((snapshot/'config.json').read_text())
        index=json.loads((snapshot/'model.safetensors.index.json').read_text())
        shards=set(index.get('weight_map',{}).values())
        if config.get('model_type')!='qwen3' or not shards:
            return False
        required={'config.json','model.safetensors.index.json','tokenizer.json','tokenizer_config.json',*shards}
        return all((snapshot/name).is_file() and (snapshot/name).stat().st_size>0
                   for name in required if Path(name).name==name) and all(Path(name).name==name for name in required)
    except (OSError,ValueError,KeyError,TypeError):
        return False

def port_free(port):
    with socket.socket() as s:
        # Ignore closed connections in TIME_WAIT, while rejecting active listeners.
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1",port))

def model_tmpdir(base=Path('/tmp')):
    """Return a private, short path for vLLM Unix-domain IPC sockets.

    vLLM appends UUID/socket names to TMPDIR and AF_UNIX paths have a small
    platform limit. The checkout-local .runtime path can exceed it in worktrees.
    """
    profile=re.sub(r'[^a-z0-9-]','',PROFILE.lower()) or 'model'
    path=Path(base)/f'iam-{os.getuid()}-{profile}-{VPORT}'
    if len(str(path))+52>=104:
        path=Path(base)/f'i{os.getuid()}-{VPORT}'
    try:
        path.mkdir(mode=0o700,parents=False,exist_ok=True)
        info=path.lstat()
        if not path.is_dir() or path.is_symlink() or info.st_uid!=os.getuid():
            raise RuntimeError('Model temporary directory is not owned by this user.')
        path.chmod(0o700)
    except OSError as exc:
        raise RuntimeError('Could not create a private model temporary directory.') from exc
    if len(str(path))+52>=104:
        raise RuntimeError('Model temporary path is too long for local IPC sockets.')
    return path

def preflight(check_ui_port=True):
    print("Python",sys.version,"OS",Path('/etc/os-release').read_text())
    row=gpu()
    check_offload_memory(row)
    stat=os.statvfs(ROOT)
    print("Home available GiB",stat.f_bavail*stat.f_frsize/1024**3)
    cached=complete_cached_snapshot()
    required=8 if model_variant()=="awq" else (4 if cached else 30)
    if cached:print("Pinned model snapshot verified; applying cached-model runtime disk headroom.")
    if stat.f_bavail*stat.f_frsize<required*1024**3: raise RuntimeError(f"Require {required} GiB /home headroom")
    port_free(VPORT)
    if check_ui_port: port_free(UPORT)
    print("Ports checked",[VPORT,UPORT] if check_ui_port else [VPORT])
    for p in ["vllm","torch","xformers","transformers","pydantic"]+(["streamlit"] if check_ui_port else []):
        print(p,importlib.metadata.version(p))
    return row

def vllm_command(row):
    model=load_model(ROOT)
    snapshot=snapshot_path(ROOT,model)
    if model_variant()=="awq":
        if float(row[3])<8.0: raise RuntimeError("AWQ Marlin requires Ampere or newer; use fp16 on V100/V100S")
        validate_awq_snapshot(snapshot)
    if not list(snapshot.glob("*.safetensors")): raise RuntimeError("Pinned model snapshot missing; run download-model.py")
    utilization=float(os.getenv("IAM_GPU_MEMORY_UTILIZATION","0.80"))
    if not 0.1<=utilization<=0.85: raise RuntimeError("Memory utilization must be 0.1–0.85")
    if thinking_enabled() and (gpu_class(row),model_variant()) not in {('a2','awq'),('a30','fp16'),('v100','fp16'),('v100s','fp16')}:
        raise RuntimeError('Experimental thinking requires A2/AWQ or a validated FP16 profile.')
    command=[sys.executable,"-m","vllm.entrypoints.openai.api_server","--model",str(snapshot),"--served-model-name",model["model"],"--dtype","half","--host","127.0.0.1","--port",str(VPORT),"--max-model-len",str(context_tokens()),"--max-num-seqs","1","--tensor-parallel-size","1","--gpu-memory-utilization",str(utilization),"--cpu-offload-gb",str(cpu_offload(row)),"--enforce-eager","--disable-log-requests","--guided-decoding-backend","xgrammar"]
    if model_variant()=="awq": command += ["--quantization",model["quantization"]]
    if thinking_enabled():command += ['--enable-reasoning','--reasoning-parser','deepseek_r1']
    return command
def identity(pid):
    # start-time field protects against PID reuse.
    return Path(f"/proc/{pid}/stat").read_text().split(") ",1)[1].split()[19]

def wait_for_exit(pid, start_time, timeout=15, *, clock=time.monotonic, sleep=time.sleep):
    """Wait for this exact process instance to disappear; never signal a replacement PID."""
    deadline=clock()+timeout
    while True:
        try:current=identity(pid)
        except FileNotFoundError:return True
        if current!=start_time:return True
        if clock()>=deadline:return False
        sleep(min(.1,max(0,deadline-clock())))
def recover_record(kind):
    """Recover only this user's exact project supervisor, never a port owner."""
    matches=[]
    for procdir in Path('/proc').glob('[0-9]*'):
        try:
            if procdir.stat().st_uid!=os.getuid():continue
            args=[part.decode() for part in (procdir/'cmdline').read_bytes().split(b'\0') if part]
            if len(args)!=4 or args[0]!=sys.executable or args[1]!=str(ROOT/'scripts/supervise.py') or args[2]!=kind:continue
            command=json.loads(args[3])
            if kind=='ui' and command[:5]!=[sys.executable,'-m','streamlit','run',str(ROOT/'app.py')]:continue
            pid=int(procdir.name)
            if os.getpgid(pid)!=pid:continue
            matches.append({'pid':pid,'start_time':identity(pid),'command':args,'root':str(ROOT)})
        except (OSError,ValueError,IndexError,UnicodeError):continue
    if len(matches)>1:raise RuntimeError('Multiple project supervisors found; refusing automatic recovery')
    if matches:
        RUNTIME.mkdir(exist_ok=True)
        (RUNTIME/(kind+'.pid.json')).write_text(json.dumps(matches[0]))
        print('Recovered project-owned',kind,'supervisor PID',matches[0]['pid'])
        return True
    return False
def start(kind):
    RUNTIME.mkdir(exist_ok=True)
    record=RUNTIME/(kind+".pid.json")
    if not record.exists():recover_record(kind)
    if record.exists():
        old=json.loads(record.read_text())
        try:
            if identity(old['pid'])==old['start_time']: raise RuntimeError("Project process already running")
        except FileNotFoundError: pass
    env=os.environ.copy()
    env.update({"PYTHONPATH":str(ROOT/"src"),"OMP_NUM_THREADS":"2","MKL_NUM_THREADS":"2","OPENBLAS_NUM_THREADS":"2","NUMEXPR_NUM_THREADS":"2","RAYON_NUM_THREADS":"2","TOKENIZERS_PARALLELISM":"false","HF_HOME":str(RUNTIME/"huggingface"),"TMPDIR":str(model_tmpdir()),"IAM_BASE_URL":BASE_URL,"VLLM_NO_USAGE_STATS":"1","DO_NOT_TRACK":"1"})
    if kind=="vllm":
        row=preflight(check_ui_port=False)
        env.update({"IAM_MODEL_VARIANT":model_variant(),"IAM_MODEL_THINKING":'1' if thinking_enabled() else '0',"CUDA_VISIBLE_DEVICES":row[0],"CUDA_DEVICE_ORDER":"PCI_BUS_ID","VLLM_USE_V1":"0","VLLM_ATTENTION_BACKEND":"XFORMERS","IAM_GPU_PROFILE":PROFILE})
        cmd=vllm_command(row)
    else:
        port_free(UPORT)
        cmd=[sys.executable,"-m","streamlit","run",str(ROOT/"app.py"),"--server.address","127.0.0.1","--server.port",str(UPORT),"--server.headless","true","--browser.gatherUsageStats","false"]
    # A supervisor rotates logs, handles signals, and owns a dedicated process group.
    supervisor=[sys.executable,str(ROOT/"scripts/supervise.py"),kind,json.dumps(cmd)]
    proc=subprocess.Popen(supervisor,cwd=ROOT,env=env,start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    record.write_text(json.dumps({"pid":proc.pid,"start_time":identity(proc.pid),"command":supervisor,"root":str(ROOT),"environment":{k:env[k] for k in ["OMP_NUM_THREADS","MKL_NUM_THREADS","OPENBLAS_NUM_THREADS","NUMEXPR_NUM_THREADS","RAYON_NUM_THREADS","TOKENIZERS_PARALLELISM","HF_HOME","TMPDIR","IAM_BASE_URL"]+(["IAM_MODEL_VARIANT","IAM_MODEL_THINKING","CUDA_VISIBLE_DEVICES","CUDA_DEVICE_ORDER","VLLM_USE_V1","VLLM_ATTENTION_BACKEND","IAM_GPU_PROFILE"] + (["IAM_SRA_MODEL_LEASE_ID"] if "IAM_SRA_MODEL_LEASE_ID" in env else []) if kind=="vllm" else [])}}))
    print(kind,"supervisor PID",proc.pid,"log",RUNTIME/(kind+".log"))
def stop(kind):
    record=RUNTIME/(kind+".pid.json")
    if not record.exists() and not recover_record(kind): print("No project-owned",kind,"process found");return
    info=json.loads(record.read_text())
    try:
        actual=Path(f"/proc/{info['pid']}/cmdline").read_bytes().split(b"\0")
        expected=[x.encode() for x in info['command']]
        if info['root']!=str(ROOT) or identity(info['pid'])!=info['start_time'] or actual[:-1]!=expected or os.getpgid(info['pid'])!=info['pid']:
            raise RuntimeError("Process identity mismatch; refusing to signal")
        os.killpg(info['pid'],signal.SIGTERM)
        if not wait_for_exit(info['pid'],info['start_time']):
            raise RuntimeError("Owned project process did not exit; retaining its record for safe recovery")
        print("Stopped project-owned",kind)
    except FileNotFoundError:
        # A restricted PID namespace may hide a still-running host process.
        print("Project process is not visible here; retaining its record. Run this command in the terminal that launched it.")
        return
    record.unlink()
def health():
    import httpx
    failures=[]
    with httpx.Client(timeout=10,trust_env=False) as c:
        for name,url in [("vllm",f"{BASE_URL}/health"),("streamlit",f"http://127.0.0.1:{UPORT}/_stcore/health")]:
            try:
                r=c.get(url);r.raise_for_status();print(name,"healthy")
            except httpx.HTTPError as exc:
                failures.append(name);print(name,"unavailable",type(exc).__name__)
    if failures: raise RuntimeError("Unhealthy services: "+", ".join(failures))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("action",choices=["preflight","start","stop","health"]);p.add_argument("kind",nargs="?",choices=["vllm","ui"]);a=p.parse_args()
    try:
        if a.action=="preflight":preflight(check_ui_port=a.kind!="vllm")
        elif a.action=="health":health()
        elif not a.kind:p.error("start/stop requires vllm or ui")
        elif a.action=="start":start(a.kind)
        else:stop(a.kind)
    except Exception as exc:print(str(exc),file=sys.stderr);sys.exit(1)
