"""Prepare a separate local demo without reading or replacing the real .env."""
import os
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]
ACCOUNTS = (
    ("Responsável FLIKE", "responsavel@example.com"),
    ("Visitante FLIKE", "visitante@example.com"),
    ("Responsável de outra instituição", "outro@example.com"),
)


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
    import httpx
    if os.environ.get("DB_DATABASE") != "flike_demo":
        raise SystemExit("Seed permitido apenas no banco isolado flike_demo.")
    if os.environ.get("DEMO_API_URL") not in ("http://127.0.0.1:18000", "http://localhost:18000"):
        raise SystemExit("Seed permitido apenas na API local de demonstração, porta 18000.")
    password = os.environ["DEMO_PASSWORD"]
    with httpx.Client(base_url=os.environ["DEMO_API_URL"], timeout=20) as client:
        tokens = {}
        for name, email in ACCOUNTS:
            response = client.post("/user/new", json={"name": name, "email": email, "password": password})
            if response.status_code not in (200, 201, 409):
                response.raise_for_status()
            response = client.post("/auth/user", json={"email": email, "password": password})
            response.raise_for_status()
            tokens[email] = {"Authorization": "Bearer " + response.json()["token"]}
        for email, name in ((ACCOUNTS[0][1], "FLIKE — Demonstração"), (ACCOUNTS[2][1], "Instituição independente")):
            headers = tokens[email]
            def call(method, path, **kwargs):
                response = client.request(method, path, headers=headers, **kwargs)
                response.raise_for_status()
                return response.json()
            institutions = call("GET", "/admin/institutions")
            institution = next((row for row in institutions if row["name"] == name), None)
            institution_id = institution["id"] if institution else call("POST", "/admin/institutions", json={"name": name})["institution_id"]
            buildings = call("GET", "/admin/buildings")
            building = next((row for row in buildings if row["institution_id"] == institution_id and row["name"] == "Edifício de demonstração"), None)
            building_id = building["id"] if building else call("POST", "/admin/buildings", json={
                "institution_id": institution_id, "name": "Edifício de demonstração",
                "address_line_1": "Endereço demonstrativo", "address_line_2": "",
                "city": "São Paulo", "state": "SP", "zip_code": "01000-000", "country": "Brasil",
            })["building_id"]
            rooms = call("GET", "/admin/rooms")
            room = next((row for row in rooms if row["building_id"] == building_id and row["number"] == "101"), None)
            room_id = room["id"] if room else call("POST", "/admin/rooms", json={
                "building_id": building_id, "name": "Sala de apoio", "number": "101",
            })["room_id"]
            locks = call("GET", "/admin/locks")
            if not any(row["room_id"] == room_id for row in locks):
                call("POST", "/admin/locks", json={"room_id": room_id})
    print("Contas e duas instituições prontas; uma tranca por sala. Seed pode ser repetido.")
    access = ROOT / ".demo" / "ACESSO.md"
    access.parent.mkdir(exist_ok=True)
    with os.fdopen(os.open(access, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as stream:
        stream.write("# Acesso à demonstração local\n\nSite: http://127.0.0.1:3000\n\n")
        stream.write("\n".join(f"- {name}: `{email}`" for name, email in ACCOUNTS))
        stream.write(f"\n\nSenha das três contas fictícias: `{password}`\n")
    print("Consulte ./scripts/demo.sh credentials para os logins locais.")


def credentials():
    print("Contas fictícias para esta demonstração local:")
    for name, email in ACCOUNTS:
        print(f"  {name}: {email}")
    print("Senha comum:", os.environ["DEMO_PASSWORD"])


if __name__ == "__main__":
    actions = {"init": initialize, "seed": seed, "credentials": credentials}
    if len(sys.argv) != 2 or sys.argv[1] not in actions:
        raise SystemExit("Uso: demo.py init|seed|credentials")
    actions[sys.argv[1]]()
