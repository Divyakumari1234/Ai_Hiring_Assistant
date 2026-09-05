"""Run the private Python API and public Next.js server in one container."""

import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def main():
    if not os.environ.get("REVIEW_PASSWORD"):
        raise SystemExit("Set REVIEW_PASSWORD before exposing the company workspace")
    root = Path(__file__).resolve().parents[1]
    processes = []

    def stop(*_):
        for process in processes:
            if process.poll() is None:
                process.terminate()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        backend = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app",
                                    "--host", "127.0.0.1", "--port", "8000"], cwd=root / "backend")
        processes.append(backend)
        for _ in range(30):
            if backend.poll() is not None:
                raise RuntimeError("Backend exited during startup")
            try:
                with urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=1):
                    break
            except OSError:
                time.sleep(1)
        else:
            raise RuntimeError("Backend did not become ready")
        processes.append(subprocess.Popen(["node", "server.js"], cwd=root / "frontend"))
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
    finally:
        stop()
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    return 1


if __name__ == "__main__":
    sys.exit(main())
