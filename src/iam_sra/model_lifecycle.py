"""Optional review-only A2 lifecycle. No model starts on page/status requests.

The normal application remains always-on. The sharing launcher opts into this
single-process lease, using the existing model launcher and workload guards.
Only a model marked as started by this review may be released automatically.
"""
import atexit
from contextlib import contextmanager, nullcontext
import importlib.util
import json
import logging
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit
from uuid import uuid4

from .assessment import AssessmentError
from .settings import ROOT

_log = logging.getLogger(__name__)


class ProjectA2:
    def __init__(self, port, *, root=ROOT, gpu_uuid=None):
        self.port, self.root, self.gpu_uuid = port, Path(root), gpu_uuid
        self.record = self.root / '.runtime/vllm.pid.json'
        self.marker = self.root / '.runtime/fn-review/model-owner.json'

    def verified_record(self):
        """Exact live process/group, uid, start time, checkout, profile and port."""
        try:
            row = json.loads(self.record.read_text())
            proc = Path('/proc') / str(int(row['pid']))
            started = (proc / 'stat').read_text().split(') ', 1)[1].split()[19]
            command = (proc / 'cmdline').read_bytes().rstrip(b'\0').decode().split('\0')
            if (proc.stat().st_uid == os.getuid() and row['root'] == str(self.root)
                    and started == row['start_time'] and command == row['command']
                    and command[1:3] == [str(self.root / 'scripts/supervise.py'), 'vllm']
                    and os.getpgid(row['pid']) == row['pid']
                    and row['environment'].get('IAM_GPU_PROFILE') == 'liono-a2'
                    and row['environment'].get('IAM_BASE_URL') == f'http://127.0.0.1:{self.port}'):
                return row
        except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError):
            pass
        return None

    def _marker(self):
        try:
            value = json.loads(self.marker.read_text())
            return value if isinstance(value, dict) else None
        except (OSError, ValueError):
            return None

    def _owns(self, row, marker):
        return bool(row and marker and marker.get('port') == self.port and (
            (marker.get('lease_id') and row['environment'].get('IAM_SRA_MODEL_LEASE_ID') == marker['lease_id'])
            or (marker.get('record') and marker['record'] == row)))

    def owns_running_model(self):
        return self._owns(self.verified_record(), self._marker())

    def _write_marker(self, data):
        self.marker.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = self.marker.with_suffix('.tmp')
        temporary.write_text(json.dumps(data))
        temporary.chmod(0o600)
        temporary.replace(self.marker)

    def _forget_marker(self, expected):
        if self._marker() == expected:
            self.marker.unlink(missing_ok=True)

    def _idle_gpu_uuid(self):
        # Reuse the exact supported-device selector, then also reject small
        # compute jobs below its historical 2 GiB occupied-memory threshold.
        spec = importlib.util.spec_from_file_location('iam_sra_review_ops', self.root / 'scripts/ops.py')
        ops = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ops)
        ops.PROFILE, ops.UUID = 'liono-a2', self.gpu_uuid or ''
        row = ops.gpu()
        processes = subprocess.check_output(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid',
            '--format=csv,noheader,nounits'], text=True, timeout=10)
        if any(line.split(',')[0].strip() == row[1] for line in processes.splitlines() if ',' in line):
            raise AssessmentError('Shared GPU has an active compute process.', code='gpu_unavailable')
        return row[1]

    def start(self, deadline):
        if socket.gethostname().split('.')[0] != 'liono':
            raise AssessmentError('Shared GPU unavailable.', code='gpu_unavailable')
        if self.owns_running_model():
            return
        if self.marker.exists():
            raise AssessmentError('Previous review model ownership cannot be verified.', code='gpu_unavailable')
        try:
            selected_uuid = self._idle_gpu_uuid()
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
            raise AssessmentError('Shared GPU unavailable; retry later.', code='gpu_unavailable') from None
        # A unique per-start marker prevents adopting another operator's model
        # if their launch wins a concurrent start race. It is never exported.
        marker = {'port': self.port, 'lease_id': uuid4().hex}
        self._write_marker(marker)
        env = os.environ.copy()
        env['IAM_SRA_MODEL_LEASE_ID'] = marker['lease_id']
        command = [sys.executable, str(self.root / 'scripts/model-host.py'),
                   'start', 'liono-a2', '--port', str(self.port)]
        command += ['--gpu-uuid', selected_uuid]
        try:
            remaining = min(610, deadline - time.monotonic())
            if remaining <= 0:
                raise AssessmentError('Model startup timed out.', code='timeout')
            subprocess.run(command, cwd=self.root, env=env, timeout=remaining,
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if not self.owns_running_model():
                raise AssessmentError('Shared GPU unavailable.', code='gpu_unavailable')
        except (OSError, subprocess.SubprocessError, AssessmentError):
            # A failed readiness wait may still have started a supervised model.
            if self.owns_running_model():
                self.stop()
            else:
                self._forget_marker(marker)
            raise AssessmentError('Shared GPU unavailable; retry later.', code='gpu_unavailable') from None

    def stop(self):
        marker = self._marker()
        if marker is None:
            return not self.marker.exists() and self.verified_record() is None
        row = self.verified_record()
        if not self._owns(row, marker):
            _log.warning('review_gpu_release_refused_identity_not_verified')
            return False
        pid = row['pid']
        try:
            os.killpg(pid, signal.SIGTERM)
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                try:
                    os.killpg(pid, 0)
                except ProcessLookupError:
                    break
                time.sleep(.1)
            else:
                if self.verified_record() != row:
                    return False  # Reverify identity before escalating a signal.
                os.killpg(pid, signal.SIGKILL)
                # Wait for the entire owned process group, not only its supervisor.
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    try:
                        os.killpg(pid, 0)
                    except ProcessLookupError:
                        break
                    time.sleep(.1)
                else:
                    return False
        except ProcessLookupError:
            pass
        except PermissionError:
            return False
        # Never delete a replacement process record written by another start.
        try:
            if json.loads(self.record.read_text()) == row:
                self.record.unlink()
        except (OSError, ValueError):
            pass
        self._forget_marker(marker)
        return True

    def release_existing(self):
        """Explicit migration from the old always-on review launcher only."""
        row = self.verified_record()
        if row is None:
            return False
        self._write_marker({'port': self.port, 'record': row})
        return self.stop()


class OnDemandModel:
    def __init__(self, backend, idle_seconds=60, *, clock=time.monotonic):
        self.backend, self.idle_seconds, self.clock = backend, idle_seconds, clock
        self.lock = threading.RLock()
        self.active = 0
        self.running = backend.owns_running_model()
        self.state = 'ready' if self.running else 'idle'
        self.last_use = clock()
        self.retry_at = 0
        self.closed = False
        self.stopped = threading.Event()

    @contextmanager
    def lease(self, deadline):
        with self.lock:
            if self.closed or self.clock() < self.retry_at or (self.running and self.state == 'unavailable'):
                raise AssessmentError('Shared GPU unavailable; retry later.', code='gpu_unavailable')
            if not self.running:
                self.state = 'loading'
                try:
                    self.backend.start(deadline)
                except Exception:
                    self.state = 'unavailable'
                    self.running = self.backend.owns_running_model()
                    self.last_use = self.clock()
                    self.retry_at = self.clock() + 15
                    raise AssessmentError('Shared GPU unavailable; retry later.', code='gpu_unavailable') from None
                self.running = True
            self.state = 'ready'
            self.active += 1
        try:
            yield
        finally:
            with self.lock:
                self.active -= 1
                self.last_use = self.clock()
                if self.closed and not self.active:
                    self._release()

    def _release(self):
        self.state = 'releasing'
        try:
            released = self.backend.stop()
        except Exception:
            _log.warning('review_gpu_release_failed')
            released = False
        if released:
            self.running = False
            self.state = 'idle'
        else:
            self.state = 'unavailable'
            self.retry_at = self.clock() + 15

    def release_if_idle(self):
        with self.lock:
            if self.running and not self.active and self.clock() >= self.retry_at and self.clock() - self.last_use >= self.idle_seconds:
                self._release()

    def watch(self):
        while not self.stopped.wait(1):
            self.release_if_idle()

    def close(self):
        self.stopped.set()
        with self.lock:
            self.closed = True
            if self.running and not self.active:
                self._release()

    def status(self):
        # No lock: startup can take minutes. Status must remain nonblocking.
        return {'mode': 'on_demand', 'state': self.state, 'idle_seconds': self.idle_seconds}


_manager = None
_manager_lock = threading.Lock()


def manager():
    global _manager
    if os.getenv('IAM_SRA_ON_DEMAND_GPU') != '1':
        return None
    with _manager_lock:
        if _manager is None:
            origin = urlsplit(os.environ['IAM_BASE_URL'])
            idle = int(os.getenv('IAM_SRA_GPU_IDLE_SECONDS', '60'))
            if (origin.scheme != 'http' or origin.hostname != '127.0.0.1' or not origin.port
                    or origin.username or origin.password or origin.path not in {'', '/'} or origin.query or origin.fragment
                    or not 10 <= idle <= 3600):
                raise ValueError('On-demand review requires an exact loopback model endpoint and 10–3600 idle seconds.')
            backend = ProjectA2(origin.port, gpu_uuid=os.getenv('IAM_SRA_REVIEW_GPU_UUID') or None)
            _manager = OnDemandModel(backend, idle)
            atexit.register(_manager.close)
            threading.Thread(target=_manager.watch, name='iam-sra-idle-gpu', daemon=True).start()
        return _manager


def inference_lease(base_url, deadline):
    model = manager()
    if model is None:
        return nullcontext()
    if base_url.rstrip('/') != os.environ['IAM_BASE_URL'].rstrip('/'):
        raise AssessmentError('Unexpected on-demand model endpoint.', code='gpu_unavailable')
    return model.lease(deadline)


def public_status():
    model = manager()
    return model.status() if model else {'mode': 'always_on', 'state': 'unmanaged'}
