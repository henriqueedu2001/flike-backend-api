"""Prepare a separate local demo without reading or replacing the real .env."""
import json
import os
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]
SEED_FILE = ROOT / "data" / "demo_seed.json"


def accounts():
    with SEED_FILE.open(encoding="utf-8") as stream:
        return [(row["name"], row["email"]) for row in json.load(stream)["users"]]


def initialize():
    target = ROOT / ".env.demo"
    if target.exists():
        print("Configuração de demonstração existente preservada.")
        return
    values = {
        "DB_HOST": "127.0.0.1", "DB_PORT": "55470",
        "DB_DATABASE": "flike_demo", "DB_USER": "flike_demo",
        "DB_PASSWORD": secrets.token_hex(24),
        "DEMO_DB_ROOT_PASSWORD": secrets.token_hex(24),
        "JWT_SECRET": secrets.token_hex(32),
        "DEMO_PASSWORD": "Flike-" + secrets.token_hex(8),
        "DEMO_API_URL": "http://127.0.0.1:18000",
        "CORS_ORIGINS": "http://127.0.0.1:3000,http://localhost:3000",
    }
    with os.fdopen(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as stream:
        stream.write("".join(f"{key}={value}\n" for key, value in values.items()))
    print("Configuração local criada em .env.demo (não versionada).")


def seed():
    if os.environ.get("DB_DATABASE") != "flike_demo":
        raise SystemExit("Seed permitido apenas no banco isolado flike_demo.")
    from scripts.seed_db import format_summary, load_seed_data, seed_dataset

    password = os.environ["DEMO_PASSWORD"]
    data = load_seed_data(SEED_FILE)
    result = seed_dataset(SEED_FILE)
    print(format_summary(data, result))
    access = ROOT / ".demo" / "ACESSO.md"
    access.parent.mkdir(exist_ok=True)
    with os.fdopen(os.open(access, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as stream:
        stream.write("# Acesso à demonstração local\n\nSite: http://127.0.0.1:3000\n\n")
        stream.write("\n".join(f"- {name}: `{email}`" for name, email in accounts()))
        stream.write(f"\n\nSenha comum das contas fictícias: `{password}`\n")
    print("Consulte ./scripts/demo.sh credentials para os logins locais.")


def credentials():
    print("Contas fictícias para esta demonstração local:")
    for name, email in accounts():
        print(f"  {name}: {email}")
    print("Senha comum:", os.environ["DEMO_PASSWORD"])


if __name__ == "__main__":
    actions = {"init": initialize, "seed": seed, "credentials": credentials}
    if len(sys.argv) != 2 or sys.argv[1] not in actions:
        raise SystemExit("Uso: demo.py init|seed|credentials")
    actions[sys.argv[1]]()
