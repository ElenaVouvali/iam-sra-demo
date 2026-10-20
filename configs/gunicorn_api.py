"""The in-memory store requires exactly one non-preloaded API worker."""
import os

bind = f"127.0.0.1:{int(os.getenv('IAM_SRA_API_PORT', '8001'))}"
workers = 1
worker_class = 'gthread'
threads = 8
preload_app = False
timeout = 60
graceful_timeout = 15
accesslog = None
errorlog = '-'
capture_output = False


def on_starting(server):
    if server.cfg.workers != 1 or server.cfg.preload_app:
        raise RuntimeError('IAM-SRA in-memory sessions require one worker and no preload.')
