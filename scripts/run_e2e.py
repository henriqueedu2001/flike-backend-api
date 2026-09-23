"""Build and exercise the actual browser/API against flike_test, without mocks."""
from pathlib import Path
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = Path(os.environ.get("FLIKE_FRONTEND_DIR", ROOT.parent / "flike-frontend-webpage"))


def ready(url, process):
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Serviço encerrou antes de iniciar: {url}")
        try:
            with urllib.request.urlopen(url, timeout=1):
                return
        except OSError:
            time.sleep(0.25)
    raise RuntimeError(f"Serviço não iniciou: {url}")


def main():
    if os.environ.get("DB_DATABASE") != "flike_test" or os.environ.get("FLIKE_TEST_DATABASE") != "1":
        raise SystemExit("Execute ./scripts/demo.sh e2e para usar o banco isolado.")
    for port in (18001, 3001):
        with socket.socket() as sock:
            # Closed browser connections may remain in TIME_WAIT after a previous run.
            # Match the servers' SO_REUSEADDR behavior while still rejecting a live listener.
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                raise SystemExit(f"Porta de testes {port} ocupada. Nenhum serviço existente foi encerrado.")
    env = {**os.environ, "NEXT_DIST_DIR": ".next-e2e", "NEXT_PUBLIC_API_URL": "http://127.0.0.1:18001",
           "CORS_ORIGINS": "http://127.0.0.1:3001", "E2E_WEB_URL": "http://127.0.0.1:3001",
           "E2E_API_URL": "http://127.0.0.1:18001"}
    subprocess.run(["npm", "run", "build"], cwd=FRONTEND, env=env, check=True)
    logs = ROOT / ".demo"
    logs.mkdir(exist_ok=True)
    children = []
    try:
        with (logs / "e2e-api.log").open("w") as api_log, (logs / "e2e-web.log").open("w") as web_log:
            api = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "18001"],
                                   cwd=ROOT, env=env, stdout=api_log, stderr=subprocess.STDOUT, start_new_session=True)
            children.append(api)
            ready(env["E2E_API_URL"] + "/openapi.json", api)
            web = subprocess.Popen(["npm", "run", "start", "--", "--hostname", "127.0.0.1", "--port", "3001"],
                                   cwd=FRONTEND, env=env, stdout=web_log, stderr=subprocess.STDOUT, start_new_session=True)
            children.append(web)
            ready(env["E2E_WEB_URL"] + "/login", web)
            result = subprocess.run([sys.executable, "-m", "pytest", "e2e", "-q"], cwd=ROOT, env=env)
            return result.returncode
    finally:
        for child in reversed(children):
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()


if __name__ == "__main__":
    sys.exit(main())
