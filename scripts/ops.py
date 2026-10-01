#!/usr/bin/env python3
"""Local processes only; process identity checked before any signal."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/".runtime"
UUID=os.getenv("IAM_GPU_UUID","GPU-cea3d9e4-d189-a5b9-cf2e-9bd77b8218fb")
VPORT=int(os.getenv("IAM_VLLM_PORT","8000"))
UPORT=int(os.getenv("IAM_UI_PORT","8501"))
def gpu():
    output=subprocess.check_output(["nvidia-smi","--query-gpu=index,uuid,name,compute_cap,memory.total,memory.used,driver_version","--format=csv,noheader,nounits"],text=True)
    rows=[list(map(str.strip,r.split(","))) for r in output.strip().splitlines()]
    selected=[r for r in rows if r[1]==UUID]
    if len(selected)!=1 or "V100" not in selected[0][2] or selected[0][3]!="7.0":
        raise RuntimeError("Selected UUID is not the verified Volta V100; refusing launch")
    print(output)
    return selected[0]
def port_free(port):
    with socket.socket() as s: s.bind(("127.0.0.1",port))
def preflight(check_ui_port=True):
    print("Python",sys.version,"OS",Path('/etc/os-release').read_text())
    row=gpu()
    if float(row[5])>2048: raise RuntimeError("V100 has an existing workload (>2 GiB); refusing to reserve GPU")
    stat=os.statvfs(ROOT)
    print("Home available GiB",stat.f_bavail*stat.f_frsize/1024**3)
    if stat.f_bavail*stat.f_frsize<30*1024**3: raise RuntimeError("Require 30 GiB /home headroom")
    port_free(VPORT)
    if check_ui_port: port_free(UPORT)
    print("Ports checked",[VPORT,UPORT] if check_ui_port else [VPORT])
    for p in ["vllm","torch","xformers","transformers","streamlit","pydantic"]:
        print(p,importlib.metadata.version(p))
def identity(pid):
    # start-time field protects against PID reuse.
    return Path(f"/proc/{pid}/stat").read_text().split(") ",1)[1].split()[19]
def start(kind):
    RUNTIME.mkdir(exist_ok=True)
    record=RUNTIME/(kind+".pid.json")
    if record.exists():
        old=json.loads(record.read_text())
        try:
            if identity(old['pid'])==old['start_time']: raise RuntimeError("Project process already running")
        except FileNotFoundError: pass
    env=os.environ.copy()
    env.update({"PYTHONPATH":str(ROOT/"src"),"OMP_NUM_THREADS":"2","MKL_NUM_THREADS":"2","OPENBLAS_NUM_THREADS":"2","NUMEXPR_NUM_THREADS":"2","RAYON_NUM_THREADS":"2","TOKENIZERS_PARALLELISM":"false","HF_HOME":str(RUNTIME/"huggingface"),"TMPDIR":str(RUNTIME/"tmp"),"IAM_BASE_URL":f"http://127.0.0.1:{VPORT}","VLLM_NO_USAGE_STATS":"1","DO_NOT_TRACK":"1"})
    (RUNTIME/"tmp").mkdir(exist_ok=True)
    if kind=="vllm":
        preflight(check_ui_port=False)
        env.update({"CUDA_VISIBLE_DEVICES":gpu()[0],"CUDA_DEVICE_ORDER":"PCI_BUS_ID","VLLM_USE_V1":"0","VLLM_ATTENTION_BACKEND":"XFORMERS"})
        model=json.loads((ROOT/"configs/model.json").read_text())
        snapshot=RUNTIME/"huggingface/hub/models--Qwen--Qwen3-8B/snapshots"/model['revision']
        if not list(snapshot.glob("*.safetensors")): raise RuntimeError("Pinned model snapshot missing; run download-model.py")
        utilization=float(os.getenv("IAM_GPU_MEMORY_UTILIZATION","0.80"))
        if not 0.1<=utilization<=0.85: raise RuntimeError("Memory utilization must be 0.1–0.85")
        cmd=[sys.executable,"-m","vllm.entrypoints.openai.api_server","--model",str(snapshot),"--served-model-name","Qwen/Qwen3-8B","--dtype","half","--host","127.0.0.1","--port",str(VPORT),"--max-model-len","4096","--max-num-seqs","1","--tensor-parallel-size","1","--gpu-memory-utilization",str(utilization),"--enforce-eager","--disable-log-requests","--guided-decoding-backend","xgrammar"]
    else:
        port_free(UPORT)
        cmd=[sys.executable,"-m","streamlit","run",str(ROOT/"app.py"),"--server.address","127.0.0.1","--server.port",str(UPORT),"--server.headless","true","--browser.gatherUsageStats","false"]
    # A supervisor rotates logs, handles signals, and owns a dedicated process group.
    supervisor=[sys.executable,str(ROOT/"scripts/supervise.py"),kind,json.dumps(cmd)]
    proc=subprocess.Popen(supervisor,cwd=ROOT,env=env,start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    record.write_text(json.dumps({"pid":proc.pid,"start_time":identity(proc.pid),"command":supervisor,"root":str(ROOT),"environment":{k:env[k] for k in ["OMP_NUM_THREADS","MKL_NUM_THREADS","OPENBLAS_NUM_THREADS","NUMEXPR_NUM_THREADS","RAYON_NUM_THREADS","TOKENIZERS_PARALLELISM","HF_HOME","TMPDIR","IAM_BASE_URL"]+(["CUDA_VISIBLE_DEVICES","CUDA_DEVICE_ORDER","VLLM_USE_V1","VLLM_ATTENTION_BACKEND"] if kind=="vllm" else [])}}))
    print(kind,"supervisor PID",proc.pid,"log",RUNTIME/(kind+".log"))
def stop(kind):
    record=RUNTIME/(kind+".pid.json")
    if not record.exists(): print("No project-owned",kind,"record");return
    info=json.loads(record.read_text())
    try:
        actual=Path(f"/proc/{info['pid']}/cmdline").read_bytes().split(b"\0")
        expected=[x.encode() for x in info['command']]
        if info['root']!=str(ROOT) or identity(info['pid'])!=info['start_time'] or actual[:-1]!=expected or os.getpgid(info['pid'])!=info['pid']:
            raise RuntimeError("Process identity mismatch; refusing to signal")
        os.killpg(info['pid'],signal.SIGTERM)
        print("Stopped project-owned",kind)
    except FileNotFoundError: print("Project process already exited")
    record.unlink()
def health():
    import httpx
    failures=[]
    with httpx.Client(timeout=10,trust_env=False) as c:
        for name,url in [("vllm",f"http://127.0.0.1:{VPORT}/health"),("streamlit",f"http://127.0.0.1:{UPORT}/_stcore/health")]:
            try:
                r=c.get(url);r.raise_for_status();print(name,"healthy")
            except httpx.HTTPError as exc:
                failures.append(name);print(name,"unavailable",type(exc).__name__)
    if failures: raise RuntimeError("Unhealthy services: "+", ".join(failures))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("action",choices=["preflight","start","stop","health"]);p.add_argument("kind",nargs="?",choices=["vllm","ui"]);a=p.parse_args()
    try:
        if a.action=="preflight":preflight()
        elif a.action=="health":health()
        elif not a.kind:p.error("start/stop requires vllm or ui")
        elif a.action=="start":start(a.kind)
        else:stop(a.kind)
    except Exception as exc:print(str(exc),file=sys.stderr);sys.exit(1)
