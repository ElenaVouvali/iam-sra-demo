"""Private pipe worker for smoke-fn-interview.py --backend cpu; no HTTP service.

Reuses the existing CPU benchmark. Privacy screening and response validation
remain in the parent API process, whose Python can differ from the torch Python.
"""
from contextlib import redirect_stdout
import json
import sys

from iam_sra.cpu_benchmark import CPURuntime, CPUBaselineClient


def main():
    runtime=CPURuntime(int(sys.argv[1]),int(sys.argv[2]))
    for line in sys.stdin:
        try:
            request=json.loads(line)
            if request['path'] not in {'/tokenize','/v1/chat/completions'}:
                raise ValueError('Unsupported CPU operation')
            client=CPUBaselineClient(runtime);client._start()
            # Reserve stdout exclusively for the private structured pipe.
            with redirect_stdout(sys.stderr):
                body=client._post_json(None,request['path'],request['payload'],request['stage'],request['phase'])
            response={'body':body,'diagnostics':client.last_diagnostics}
        except Exception as exc:
            print('CPU benchmark failed: '+type(exc).__name__,file=sys.stderr,flush=True)
            response={'error':'cpu_inference_failed'}
        print(json.dumps(response),flush=True)


if __name__=='__main__':main()
