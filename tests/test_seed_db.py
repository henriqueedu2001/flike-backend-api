"""Contract checks for the versioned, reproducible demo dataset."""
from datetime import datetime, timezone
import os
import struct

from app.database.database_manager import Database
from app.modules.cmac.key import DigitalKey, Key
from conftest import expect
from scripts.seed_db import DEFAULT_DATA_FILE, load_seed_data, seed_dataset


def query(sql, params=()):
    db = Database()
    try:
        db.execute(sql, params)
        return db.fetch_all()
    finally:
        db.close()


def tracked_rows(entity=None):
    sql = "SELECT reference_key, entity_type, record_id FROM demo_seed_record WHERE dataset=%s"
    params = ["flike_demo_v1"]
    if entity:
        sql += " AND entity_type=%s"
        params.append(entity)
    sql += " ORDER BY reference_key"
    return query(sql, tuple(params))


def test_demo_seed_is_idempotent_authentic_and_cryptographically_valid(client):
    data = load_seed_data(DEFAULT_DATA_FILE)
    first = seed_dataset(DEFAULT_DATA_FILE)
    first_mappings = tracked_rows()
    second = seed_dataset(DEFAULT_DATA_FILE)
    second_mappings = tracked_rows()

    assert first == second == {
        "users": 10, "institutions": 4, "buildings": 8, "rooms": 18, "locks": 18,
        "requests": 18, "approved": 9, "rejected": 4, "pending": 5, "events": 15,
    }
    assert first_mappings == second_mappings
    assert len(first_mappings) == 100

    request_counts = query("""
        SELECT q.status, COUNT(*) AS total
        FROM demo_seed_record m
        JOIN digital_key_request q ON q.id=m.record_id
        WHERE m.dataset=%s AND m.entity_type='request'
        GROUP BY q.status
    """, (data["dataset"],))
    assert {row["status"]: row["total"] for row in request_counts} == {
        "approved": 9, "rejected": 4, "pending": 5,
    }

    keys = query("""
        SELECT k.payload, k.user_id, k.digital_lock_id, k.created_at, k.expires_at, l.secret_key
        FROM demo_seed_record m
        JOIN digital_key k ON k.id=m.record_id
        JOIN digital_lock l ON l.id=k.digital_lock_id
        WHERE m.dataset=%s AND m.entity_type='key'
    """, (data["dataset"],))
    assert len(keys) == 9
    now = datetime.now(timezone.utc)
    assert sum(row["created_at"] <= now < row["expires_at"] for row in keys) == 7
    assert sum(row["expires_at"] <= now for row in keys) == 2
    for row in keys:
        payload = bytes(row["payload"])
        user_id, lock_id, issued_at, expires_at = struct.unpack(">QQQQ", payload[:32])
        assert (user_id, lock_id) == (row["user_id"], row["digital_lock_id"])
        assert issued_at == int(row["created_at"].timestamp())
        assert expires_at == int(row["expires_at"].timestamp())
        assert DigitalKey.check_digital_key_validity(payload, Key(bytes(row["secret_key"])))

    password = os.environ[data["password_env"]]
    for user in data["users"]:
        expect(client.post("/auth/user", json={"email": user["email"], "password": password}))
