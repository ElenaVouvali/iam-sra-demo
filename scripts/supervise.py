import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import signal
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
kind=sys.argv[1]
logger=logging.getLogger(kind);logger.setLevel(logging.INFO)
h=RotatingFileHandler(ROOT/".runtime"/(kind+".log"),maxBytes=2*1024*1024,backupCount=2)
logger.addHandler(h)
child=subprocess.Popen(json.loads(sys.argv[2]),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
def terminate(signum,frame):
    if child.poll() is None: child.terminate()
signal.signal(signal.SIGTERM,terminate)
signal.signal(signal.SIGINT,terminate)
for line in child.stdout: logger.info(line.rstrip())
sys.exit(child.wait())
