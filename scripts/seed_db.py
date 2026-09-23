"""Load the versioned demo scenario directly into the configured MySQL database.

The seed is intentionally idempotent.  A small bookkeeping table records only
the rows owned by this dataset, allowing the script to refresh relative dates
without duplicating requests, keys, or event logs.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import mysql.connector

from app.modules.auth.hashes import secure_hash
from app.modules.cmac.key import DigitalKey, Key
from app.services.env import get_env_variables
from scripts.create_db import validate_existing_schema


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_FILE = ROOT / "data" / "demo_seed.json"
TRACKING_TABLE = "demo_seed_record"
ENTITY_TABLES = {
    "user": "user",
    "institution": "institution",
    "building": "building",
    "room": "room",
    "lock": "digital_lock",
    "request": "digital_key_request",
    "key": "digital_key",
    "event": "event_log",
}


class SeedDataError(ValueError):
    """The JSON scenario is malformed or internally inconsistent."""


def load_seed_data(path: Path = DEFAULT_DATA_FILE) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as stream:
            data = json.load(stream)
    except FileNotFoundError:
        raise SeedDataError(f"Arquivo de seed não encontrado: {path}") from None
    except json.JSONDecodeError as error:
        raise SeedDataError(f"JSON inválido em {path}: {error}") from None
    validate_seed_data(data)
    return data


def _require_fields(item: dict[str, Any], fields: set[str], context: str) -> None:
    missing = fields - item.keys()
    if missing:
        raise SeedDataError(f"{context}: campos ausentes: {', '.join(sorted(missing))}")


def _refs(data: dict[str, Any], section: str) -> set[str]:
    values = [item.get("ref") for item in data[section]]
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise SeedDataError(f"{section}: toda entrada precisa de uma referência textual não vazia")
    duplicates = [ref for ref, count in Counter(values).items() if count > 1]
    if duplicates:
        raise SeedDataError(f"{section}: referências duplicadas: {', '.join(sorted(duplicates))}")
    return set(values)


def validate_seed_data(data: dict[str, Any]) -> None:
    sections = ("users", "institutions", "buildings", "rooms", "locks", "requests", "events")
    if not isinstance(data, dict):
        raise SeedDataError("A raiz do arquivo deve ser um objeto JSON")
    _require_fields(data, {"dataset", "password_env", *sections}, "raiz")
    if not isinstance(data["dataset"], str) or not data["dataset"].strip():
        raise SeedDataError("dataset deve ser um texto não vazio")
    if len(data["dataset"]) > 64:
        raise SeedDataError("dataset deve ter no máximo 64 caracteres")
    if not isinstance(data["password_env"], str) or not data["password_env"].strip():
        raise SeedDataError("password_env deve indicar uma variável de ambiente")
    for section in sections:
        if not isinstance(data[section], list):
            raise SeedDataError(f"{section} deve ser uma lista")

    refs = {section: _refs(data, section) for section in sections}
    required = {
        "users": {"ref", "name", "email"},
        "institutions": {"ref", "owner", "name"},
        "buildings": {"ref", "institution", "name", "address_line_1", "address_line_2", "city", "state", "zip_code", "country"},
        "rooms": {"ref", "building", "name", "number"},
        "locks": {"ref", "room"},
        "requests": {"ref", "user", "lock", "status", "created_hours_ago"},
        "events": {"ref", "lock", "type", "log", "created_hours_ago"},
    }
    for section, fields in required.items():
        for index, item in enumerate(data[section]):
            if not isinstance(item, dict):
                raise SeedDataError(f"{section}[{index}] deve ser um objeto")
            _require_fields(item, fields, f"{section}[{index}]")

    emails = [item["email"].strip().lower() for item in data["users"]]
    duplicate_emails = [email for email, count in Counter(emails).items() if count > 1]
    if duplicate_emails:
        raise SeedDataError("users: e-mails duplicados: " + ", ".join(sorted(duplicate_emails)))
    for item in data["institutions"]:
        if item["owner"] not in refs["users"]:
            raise SeedDataError(f"institutions/{item['ref']}: owner desconhecido: {item['owner']}")
    for item in data["buildings"]:
        if item["institution"] not in refs["institutions"]:
            raise SeedDataError(f"buildings/{item['ref']}: institution desconhecida: {item['institution']}")
    for item in data["rooms"]:
        if item["building"] not in refs["buildings"]:
            raise SeedDataError(f"rooms/{item['ref']}: building desconhecido: {item['building']}")
    lock_rooms = [item["room"] for item in data["locks"]]
    if len(lock_rooms) != len(set(lock_rooms)):
        raise SeedDataError("locks: o cenário suporta somente uma tranca por sala")
    for item in data["locks"]:
        if item["room"] not in refs["rooms"]:
            raise SeedDataError(f"locks/{item['ref']}: room desconhecida: {item['room']}")
    for item in data["requests"]:
        if item["user"] not in refs["users"] or item["lock"] not in refs["locks"]:
            raise SeedDataError(f"requests/{item['ref']}: user ou lock desconhecido")
        if item["status"] not in {"pending", "approved", "rejected"}:
            raise SeedDataError(f"requests/{item['ref']}: status inválido")
        try:
            age = float(item["created_hours_ago"])
        except (TypeError, ValueError):
            raise SeedDataError(f"requests/{item['ref']}: created_hours_ago deve ser numérico") from None
        if age < 0:
            raise SeedDataError(f"requests/{item['ref']}: created_hours_ago não pode ser negativo")
        if item["status"] != "pending":
            _require_fields(item, {"decision_delay_hours"}, f"requests/{item['ref']}")
            delay = float(item["decision_delay_hours"])
            if delay < 0 or delay > age:
                raise SeedDataError(f"requests/{item['ref']}: decisão precisa ocorrer entre a criação e agora")
        if item["status"] == "approved":
            _require_fields(item, {"validity_hours"}, f"requests/{item['ref']}")
            if float(item["validity_hours"]) <= 0:
                raise SeedDataError(f"requests/{item['ref']}: validity_hours deve ser positivo")
    for item in data["events"]:
        if item["lock"] not in refs["locks"]:
            raise SeedDataError(f"events/{item['ref']}: lock desconhecido: {item['lock']}")
        if float(item["created_hours_ago"]) < 0:
            raise SeedDataError(f"events/{item['ref']}: created_hours_ago não pode ser negativo")


class DemoSeeder:
    def __init__(self, connection, data: dict[str, Any], password: str):
        self.connection = connection
        self.cursor = connection.cursor(dictionary=True)
        self.data = data
        self.dataset = data["dataset"]
        self.password = password
        self.ids: dict[tuple[str, str], int] = {}
        self.now = datetime.now(timezone.utc).replace(microsecond=0)

    @staticmethod
    def _db_time(value: datetime) -> datetime:
        return value.astimezone(timezone.utc).replace(tzinfo=None, microsecond=0)

    @staticmethod
    def _tracking_ref(entity: str, ref: str) -> str:
        return f"{entity}:{ref}"

    def create_tracking_table(self) -> None:
        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TRACKING_TABLE} (
                dataset VARCHAR(64) NOT NULL,
                reference_key VARCHAR(191) NOT NULL,
                entity_type VARCHAR(32) NOT NULL,
                record_id INT NOT NULL,
                PRIMARY KEY (dataset, reference_key),
                UNIQUE KEY uq_demo_seed_record (dataset, entity_type, record_id)
            )
        """)
        self.connection.commit()

    def _mapped_id(self, entity: str, ref: str) -> int | None:
        key = self._tracking_ref(entity, ref)
        self.cursor.execute(
            f"SELECT entity_type, record_id FROM {TRACKING_TABLE} WHERE dataset=%s AND reference_key=%s",
            (self.dataset, key),
        )
        mapping = self.cursor.fetchone()
        if mapping is None:
            return None
        if mapping["entity_type"] != entity:
            raise SeedDataError(f"Mapeamento inconsistente para {key}")
        table = ENTITY_TABLES[entity]
        self.cursor.execute(f"SELECT id FROM `{table}` WHERE id=%s", (mapping["record_id"],))
        if self.cursor.fetchone() is not None:
            return int(mapping["record_id"])
        self.cursor.execute(
            f"DELETE FROM {TRACKING_TABLE} WHERE dataset=%s AND reference_key=%s",
            (self.dataset, key),
        )
        return None

    def _remember(self, entity: str, ref: str, record_id: int) -> int:
        key = self._tracking_ref(entity, ref)
        self.cursor.execute(f"""
            INSERT INTO {TRACKING_TABLE}(dataset, reference_key, entity_type, record_id)
            VALUES(%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE entity_type=VALUES(entity_type), record_id=VALUES(record_id)
        """, (self.dataset, key, entity, record_id))
        self.ids[(entity, ref)] = int(record_id)
        return int(record_id)

    def _resolve(self, entity: str, ref: str, natural_sql: str | None = None, params: tuple = ()) -> int | None:
        record_id = self._mapped_id(entity, ref)
        if record_id is None and natural_sql is not None:
            self.cursor.execute(natural_sql, params)
            row = self.cursor.fetchone()
            record_id = int(row["id"]) if row else None
        if record_id is not None:
            self._remember(entity, ref, record_id)
        return record_id

    def _id(self, entity: str, ref: str) -> int:
        try:
            return self.ids[(entity, ref)]
        except KeyError:
            raise SeedDataError(f"Referência não resolvida: {entity}/{ref}") from None

    def seed_users(self) -> None:
        created_at = self._db_time(self.now - timedelta(days=365))
        for item in self.data["users"]:
            email = item["email"].strip().lower()
            record_id = self._resolve("user", item["ref"], "SELECT id FROM user WHERE email=%s", (email,))
            if record_id is None:
                self.cursor.execute(
                    "INSERT INTO user(name, email, created_at) VALUES(%s, %s, %s)",
                    (item["name"], email, created_at),
                )
                record_id = int(self.cursor.lastrowid)
            else:
                self.cursor.execute("UPDATE user SET name=%s, email=%s WHERE id=%s", (item["name"], email, record_id))
            self._remember("user", item["ref"], record_id)

            salt = hashlib.sha256(f"{self.dataset}:{item['ref']}:salt".encode()).hexdigest()[:32]
            hashed_email = secure_hash(email)
            hashed_password = secure_hash(salt + self.password)
            self.cursor.execute("SELECT id FROM auth WHERE hashed_email=%s", (hashed_email,))
            credentials = self.cursor.fetchone()
            if credentials:
                self.cursor.execute(
                    "UPDATE auth SET salt=%s, hashed_password=%s WHERE id=%s",
                    (salt, hashed_password, credentials["id"]),
                )
            else:
                self.cursor.execute(
                    "INSERT INTO auth(salt, hashed_email, hashed_password) VALUES(%s, %s, %s)",
                    (salt, hashed_email, hashed_password),
                )

    def seed_institutions(self) -> None:
        created_at = self._db_time(self.now - timedelta(days=300))
        for item in self.data["institutions"]:
            owner_id = self._id("user", item["owner"])
            record_id = self._resolve(
                "institution", item["ref"],
                "SELECT id FROM institution WHERE owner_id=%s AND name=%s ORDER BY id LIMIT 1",
                (owner_id, item["name"]),
            )
            if record_id is None:
                self.cursor.execute(
                    "INSERT INTO institution(owner_id, name, created_at) VALUES(%s, %s, %s)",
                    (owner_id, item["name"], created_at),
                )
                record_id = int(self.cursor.lastrowid)
            else:
                self.cursor.execute(
                    "UPDATE institution SET owner_id=%s, name=%s WHERE id=%s",
                    (owner_id, item["name"], record_id),
                )
            self._remember("institution", item["ref"], record_id)

    def seed_buildings(self) -> None:
        created_at = self._db_time(self.now - timedelta(days=270))
        columns = ("name", "address_line_1", "address_line_2", "city", "state", "zip_code", "country")
        for item in self.data["buildings"]:
            institution_id = self._id("institution", item["institution"])
            record_id = self._resolve(
                "building", item["ref"],
                "SELECT id FROM building WHERE institution_id=%s AND name=%s ORDER BY id LIMIT 1",
                (institution_id, item["name"]),
            )
            values = tuple(item[column] for column in columns)
            if record_id is None:
                self.cursor.execute("""
                    INSERT INTO building(institution_id, name, address_line_1, address_line_2, city, state, zip_code, country, created_at)
                    VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (institution_id, *values, created_at))
                record_id = int(self.cursor.lastrowid)
            else:
                self.cursor.execute("""
                    UPDATE building SET institution_id=%s, name=%s, address_line_1=%s, address_line_2=%s,
                        city=%s, state=%s, zip_code=%s, country=%s WHERE id=%s
                """, (institution_id, *values, record_id))
            self._remember("building", item["ref"], record_id)

    def seed_rooms(self) -> None:
        created_at = self._db_time(self.now - timedelta(days=240))
        for item in self.data["rooms"]:
            building_id = self._id("building", item["building"])
            record_id = self._resolve(
                "room", item["ref"],
                "SELECT id FROM room WHERE building_id=%s AND number=%s ORDER BY id LIMIT 1",
                (building_id, item["number"]),
            )
            if record_id is None:
                self.cursor.execute(
                    "INSERT INTO room(building_id, name, number, created_at) VALUES(%s, %s, %s, %s)",
                    (building_id, item["name"], item["number"], created_at),
                )
                record_id = int(self.cursor.lastrowid)
            else:
                self.cursor.execute(
                    "UPDATE room SET building_id=%s, name=%s, number=%s WHERE id=%s",
                    (building_id, item["name"], item["number"], record_id),
                )
            self._remember("room", item["ref"], record_id)

    def seed_locks(self) -> None:
        created_at = self._db_time(self.now - timedelta(days=210))
        for item in self.data["locks"]:
            room_id = self._id("room", item["room"])
            secret = hashlib.sha256(f"{self.dataset}:{item['ref']}:demo-lock-key".encode()).digest()
            record_id = self._resolve(
                "lock", item["ref"],
                "SELECT id FROM digital_lock WHERE room_id=%s ORDER BY id LIMIT 1",
                (room_id,),
            )
            if record_id is None:
                self.cursor.execute(
                    "INSERT INTO digital_lock(room_id, secret_key, created_at) VALUES(%s, %s, %s)",
                    (room_id, secret, created_at),
                )
                record_id = int(self.cursor.lastrowid)
            else:
                self.cursor.execute(
                    "UPDATE digital_lock SET room_id=%s, secret_key=%s WHERE id=%s",
                    (room_id, secret, record_id),
                )
            self._remember("lock", item["ref"], record_id)

    def seed_requests_and_keys(self) -> None:
        for item in self.data["requests"]:
            user_id = self._id("user", item["user"])
            lock_id = self._id("lock", item["lock"])
            created_at = self.now - timedelta(hours=float(item["created_hours_ago"]))
            decided_at = None
            if item["status"] != "pending":
                decided_at = created_at + timedelta(hours=float(item["decision_delay_hours"]))

            request_id = self._resolve("request", item["ref"])
            params = (
                user_id, lock_id, item["status"],
                self._db_time(decided_at) if decided_at else None,
                self._db_time(created_at),
            )
            if request_id is None:
                self.cursor.execute("""
                    INSERT INTO digital_key_request(user_id, digital_lock_id, status, decided_at, created_at)
                    VALUES(%s, %s, %s, %s, %s)
                """, params)
                request_id = int(self.cursor.lastrowid)
            else:
                self.cursor.execute("""
                    UPDATE digital_key_request
                    SET user_id=%s, digital_lock_id=%s, status=%s, decided_at=%s, created_at=%s
                    WHERE id=%s
                """, (*params, request_id))
            self._remember("request", item["ref"], request_id)

            if item["status"] != "approved":
                continue
            issued_at = decided_at
            expires_at = issued_at + timedelta(hours=float(item["validity_hours"]))
            self.cursor.execute("SELECT secret_key FROM digital_lock WHERE id=%s", (lock_id,))
            lock = self.cursor.fetchone()
            payload = DigitalKey(
                user_id, lock_id, issued_at, expires_at, Key(bytes(lock["secret_key"]))
            ).payload
            key_ref = item["ref"]
            key_id = self._resolve(
                "key", key_ref, "SELECT id FROM digital_key WHERE request_id=%s", (request_id,)
            )
            key_params = (
                request_id, user_id, lock_id, payload,
                self._db_time(issued_at), self._db_time(expires_at),
            )
            if key_id is None:
                self.cursor.execute("""
                    INSERT INTO digital_key(request_id, user_id, digital_lock_id, payload, created_at, expires_at, used, used_at)
                    VALUES(%s, %s, %s, %s, %s, %s, FALSE, NULL)
                """, key_params)
                key_id = int(self.cursor.lastrowid)
            else:
                self.cursor.execute("""
                    UPDATE digital_key SET request_id=%s, user_id=%s, digital_lock_id=%s,
                        payload=%s, created_at=%s, expires_at=%s, used=FALSE, used_at=NULL
                    WHERE id=%s
                """, (*key_params, key_id))
            self._remember("key", key_ref, key_id)

    def seed_events(self) -> None:
        for item in self.data["events"]:
            lock_id = self._id("lock", item["lock"])
            created_at = self._db_time(
                self.now - timedelta(hours=float(item["created_hours_ago"]))
            )
            event_id = self._resolve("event", item["ref"])
            params = (lock_id, item["type"], item["log"], created_at)
            if event_id is None:
                self.cursor.execute(
                    "INSERT INTO event_log(digital_lock_id, type, log, created_at) VALUES(%s, %s, %s, %s)",
                    params,
                )
                event_id = int(self.cursor.lastrowid)
            else:
                self.cursor.execute("""
                    UPDATE event_log SET digital_lock_id=%s, type=%s, log=%s, created_at=%s WHERE id=%s
                """, (*params, event_id))
            self._remember("event", item["ref"], event_id)

    def run(self) -> dict[str, int]:
        self.create_tracking_table()
        try:
            self.connection.start_transaction()
            self.seed_users()
            self.seed_institutions()
            self.seed_buildings()
            self.seed_rooms()
            self.seed_locks()
            self.seed_requests_and_keys()
            self.seed_events()
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        return {
            "users": len(self.data["users"]),
            "institutions": len(self.data["institutions"]),
            "buildings": len(self.data["buildings"]),
            "rooms": len(self.data["rooms"]),
            "locks": len(self.data["locks"]),
            "requests": len(self.data["requests"]),
            "approved": sum(row["status"] == "approved" for row in self.data["requests"]),
            "rejected": sum(row["status"] == "rejected" for row in self.data["requests"]),
            "pending": sum(row["status"] == "pending" for row in self.data["requests"]),
            "events": len(self.data["events"]),
        }

    def close(self) -> None:
        self.cursor.close()


def seed_dataset(data_path: Path = DEFAULT_DATA_FILE) -> dict[str, int]:
    data = load_seed_data(data_path)
    password_variable = data["password_env"]
    password = os.getenv(password_variable)
    if not password:
        raise SeedDataError(
            f"Defina {password_variable} com a senha comum das contas fictícias antes de executar o seed."
        )
    env = get_env_variables()
    missing = [name for name in ("DB_HOST", "DB_USER", "DB_PASSWORD", "DB_DATABASE", "DB_PORT") if not getattr(env, name)]
    if missing:
        raise SeedDataError("Configuração de banco incompleta: " + ", ".join(missing))
    connection = mysql.connector.connect(
        host=env.DB_HOST,
        user=env.DB_USER,
        password=env.DB_PASSWORD,
        database=env.DB_DATABASE,
        port=int(env.DB_PORT),
        autocommit=False,
    )
    try:
        with connection.cursor() as schema_cursor:
            if not validate_existing_schema(schema_cursor):
                raise SeedDataError(
                    "O banco está vazio. Execute 'python -m scripts.create_db' antes do seed."
                )
        seeder = DemoSeeder(connection, data, password)
        try:
            return seeder.run()
        finally:
            seeder.close()
    finally:
        connection.close()


def format_summary(data: dict[str, Any], counts: dict[str, int]) -> str:
    return (
        f"Seed '{data['dataset']}' aplicado: "
        f"{counts['users']} usuários, {counts['institutions']} instituições, "
        f"{counts['buildings']} prédios, {counts['rooms']} salas, {counts['locks']} trancas, "
        f"{counts['requests']} solicitações "
        f"({counts['approved']} aprovadas, {counts['rejected']} rejeitadas, {counts['pending']} pendentes) "
        f"e {counts['events']} eventos."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Popula o banco FLIKE com o cenário fictício versionado.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_FILE, help="arquivo JSON do cenário")
    parser.add_argument("--validate-only", action="store_true", help="valida o JSON sem acessar o banco")
    args = parser.parse_args(argv)
    try:
        data = load_seed_data(args.data)
        if args.validate_only:
            print(f"Seed válido: {args.data} ({data['dataset']}).")
            return 0
        counts = seed_dataset(args.data)
    except (SeedDataError, mysql.connector.Error) as error:
        parser.exit(1, f"Erro ao popular o banco: {error}\n")
    print(format_summary(data, counts))
    print("A execução é idempotente; repita o comando para restaurar e atualizar a linha do tempo fictícia.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
