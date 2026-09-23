"""Black-box API checks backed by an actual, isolated MySQL instance."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os
import struct
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives import cmac
from cryptography.hazmat.primitives.ciphers import algorithms

from app.database.database_manager import Database
from app.modules.cmac.key import DigitalKey, Key
from conftest import expect


def query(sql, params=()):
    db = Database()
    try:
        db.execute(sql, params)
        return db.fetch_all()
    finally:
        db.close()


def no_secret(value):
    if isinstance(value, dict):
        assert not {"secret_key", "hashed_password", "salt", "hashed_email"}.intersection(value)
        for item in value.values():
            no_secret(item)
    elif isinstance(value, list):
        for item in value:
            no_secret(item)


def test_canonical_thesis_vector():
    payload = DigitalKey.get_digital_key_payload(
        17, 23, datetime.fromtimestamp(1770000000, timezone.utc),
        datetime.fromtimestamp(1770086400, timezone.utc), Key(bytes(range(32))),
    )
    assert len(payload) == 48
    assert payload[:32] == struct.pack(">QQQQ", 17, 23, 1770000000, 1770086400)
    assert payload[32:].hex() == "2e9810209a166e7e1a61ece325657c45"
    for offset in (0, 8, 16, 24):
        modified = bytearray(payload)
        modified[offset] ^= 1
        assert not DigitalKey.check_digital_key_validity(bytes(modified), Key(bytes(range(32))))


def test_signup_duplicate_and_bad_auth(client, world):
    actor = world["visitor"]
    expect(client.post("/user/new", json={"name": "Duplicado", "email": actor["email"], "password": world["password"]}), 409)
    expect(client.post("/auth/user", json={"email": actor["email"], "password": "errada"}), 401)
    expect(client.post("/user/new", json={"name": "", "email": "invalido", "password": ""}), 422)
    rows = query("SELECT COUNT(*) AS total FROM user WHERE email = %s", (actor["email"],))
    assert rows[0]["total"] == 1


@pytest.mark.parametrize("path", ["/user/me", "/user/all", "/digital_key", "/digital_key/all", "/digital_key/requests", "/admin/institutions", "/admin/buildings", "/admin/rooms", "/admin/locks", "/admin/keys/requests", "/admin/key-holders"])
def test_sensitive_routes_require_session(client, path):
    assert client.get(path).status_code in (401, 403)


def test_expired_token(client, world):
    token = jwt.encode({"user_id": world["visitor"]["id"], "exp": datetime.now(timezone.utc) - timedelta(seconds=1)}, os.environ["JWT_SECRET"], algorithm="HS256")
    expect(client.get("/user/me", headers={"Authorization": f"Bearer {token}"}), 401)


@pytest.mark.parametrize("entity,key,data", [
    ("institutions", "institution", {"name": "Tentativa externa"}),
    ("buildings", "building", None),
    ("rooms", "room", None),
    ("locks", "lock", None),
])
def test_owner_only_crud_and_referenced_delete(client, world, entity, key, data):
    owner, other = world["owner"], world["other"]
    if entity == "buildings":
        data = owner["building_data"]
    elif entity == "rooms":
        data = {"building_id": owner["building"], "name": "Sala", "number": "101"}
    elif entity == "locks":
        data = {"room_id": owner["room"]}
    path = f"/admin/{entity}/{owner[key]}"
    expect(client.put(path, headers=other["headers"], json=data), 403)
    expect(client.delete(path, headers=other["headers"]), 403)
    expect(client.put(path, headers=owner["headers"], json=data))
    if entity != "locks":
        expect(client.delete(path, headers=owner["headers"]), 409)
    listed = expect(client.get(f"/admin/{entity}", headers=other["headers"]))
    assert owner[key] not in {row["id"] for row in listed}


def test_cannot_move_resources_to_another_owner(client, world):
    owner, other = world["owner"], world["other"]
    expect(client.put(f'/admin/buildings/{owner["building"]}', headers=owner["headers"], json={**owner["building_data"], "institution_id": other["institution"]}), 403)
    expect(client.put(f'/admin/rooms/{owner["room"]}', headers=owner["headers"], json={"building_id": other["building"], "name": "Sala", "number": "101"}), 403)
    expect(client.put(f'/admin/locks/{owner["lock"]}', headers=owner["headers"], json={"room_id": other["room"]}), 403)


def test_pending_approved_key_and_authorized_history(client, world, new_request):
    request_id = new_request()
    visitor, owner, other = world["visitor"], world["owner"], world["other"]
    requests = expect(client.get("/digital_key/requests?status=pending", headers=visitor["headers"]))
    assert any(row["id"] == request_id for row in requests)
    assert all(row["id"] != request_id for row in expect(client.get("/digital_key/requests", headers=other["headers"])))
    for actor in (visitor, other):
        expect(client.post(f"/admin/keys/requests/{request_id}/approve", headers=actor["headers"], json={}), 403)
        expect(client.post(f"/admin/keys/requests/{request_id}/reject", headers=actor["headers"]), 403)
    approved = expect(client.post(f"/admin/keys/requests/{request_id}/approve", headers=owner["headers"], json={}))
    key_id = approved["digital_key_id"]
    key = expect(client.get(f"/digital_key?key_id={key_id}", headers=visitor["headers"]))
    no_secret(key)
    assert key["request_id"] == request_id
    assert key["user_id"] == visitor["id"]
    assert key["digital_lock_id"] == owner["lock"]
    payload = bytes.fromhex(key["payload"])
    assert len(payload) == 48
    user_id, lock_id, issued, expires = struct.unpack(">QQQQ", payload[:32])
    assert (user_id, lock_id) == (visitor["id"], owner["lock"])
    assert expires - issued == 24 * 60 * 60
    assert int(datetime.fromisoformat(key["expires_at"].replace("Z", "+00:00")).timestamp()) == expires
    secret = query("SELECT secret_key FROM digital_lock WHERE id=%s", (lock_id,))[0]["secret_key"]
    verifier = cmac.CMAC(algorithms.AES(bytes(secret)))
    verifier.update(payload[:32])
    verifier.verify(payload[32:])
    for _ in range(2):
        assert expect(client.get(f"/digital_key?key_id={key_id}", headers=visitor["headers"]))["payload"] == key["payload"]
    expect(client.get(f"/digital_key?key_id={key_id}", headers=other["headers"]), 403)
    expect(client.get(f'/digital_key?id={visitor["id"]}', headers=other["headers"]), 403)
    history = expect(client.get(f'/admin/key-holders/{visitor["id"]}/history', headers=owner["headers"]))
    assert any(row["digital_lock_id"] == lock_id for row in history)
    assert not any(row["digital_lock_id"] == lock_id for row in expect(client.get(f'/admin/key-holders/{visitor["id"]}/history', headers=other["headers"])))
    no_secret(history)
    expect(client.post(f"/admin/keys/requests/{request_id}/approve", headers=owner["headers"], json={}), 409)
    expect(client.post(f"/admin/keys/requests/{request_id}/reject", headers=owner["headers"]), 409)
    expect(client.delete(f"/admin/locks/{lock_id}", headers=owner["headers"]), 409)
    assert query("SELECT COUNT(*) AS total FROM digital_key WHERE request_id=%s", (request_id,))[0]["total"] == 1


def test_rejection_never_issues_key(client, world, new_request):
    request_id = new_request()
    expect(client.post(f"/admin/keys/requests/{request_id}/reject", headers=world["owner"]["headers"]))
    assert any(row["id"] == request_id for row in expect(client.get("/digital_key/requests?status=rejected", headers=world["visitor"]["headers"])))
    assert query("SELECT COUNT(*) AS total FROM digital_key WHERE request_id=%s", (request_id,))[0]["total"] == 0
    expect(client.post(f"/admin/keys/requests/{request_id}/approve", headers=world["owner"]["headers"], json={}), 409)


@pytest.mark.parametrize("decisions", [("approve", "approve"), ("approve", "reject")])
def test_concurrent_decisions_emit_at_most_once(client, world, new_request, decisions):
    request_id = new_request()
    def decide(decision):
        return client.post(f"/admin/keys/requests/{request_id}/{decision}", headers=world["owner"]["headers"], json={}).status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(decide, decisions))
    assert sorted(statuses) == [200, 409]
    status = query("SELECT status FROM digital_key_request WHERE id=%s", (request_id,))[0]["status"]
    assert query("SELECT COUNT(*) AS total FROM digital_key WHERE request_id=%s", (request_id,))[0]["total"] == (1 if status == "approved" else 0)


def test_failed_decision_rolls_back_key(client, world, new_request, monkeypatch):
    request_id = new_request()
    original = Database.execute
    def fail_on_transition(self, sql, params=None):
        if "UPDATE digital_key_request" in " ".join(sql.split()):
            raise RuntimeError("injected failure after key insertion")
        return original(self, sql, params)
    with monkeypatch.context() as context:
        context.setattr(Database, "execute", fail_on_transition)
        response = client.post(f"/admin/keys/requests/{request_id}/approve", headers=world["owner"]["headers"], json={})
        assert response.status_code == 500
    assert query("SELECT COUNT(*) AS total FROM digital_key WHERE request_id=%s", (request_id,))[0]["total"] == 0
    assert query("SELECT status FROM digital_key_request WHERE id=%s", (request_id,))[0]["status"] == "pending"
    expect(client.post(f"/admin/keys/requests/{request_id}/approve", headers=world["owner"]["headers"], json={}))


@pytest.mark.parametrize("expiry", ["2020-01-01T00:00:00Z", "2099-01-01T00:00:00", "not-a-date"])
def test_invalid_expiration_does_not_change_request(client, world, new_request, expiry):
    request_id = new_request()
    expect(client.post(f"/admin/keys/requests/{request_id}/approve", headers=world["owner"]["headers"], json={"expires_at": expiry}), 422)
    assert query("SELECT status FROM digital_key_request WHERE id=%s", (request_id,))[0]["status"] == "pending"


def test_expiration_offset_matches_payload(client, world, new_request):
    request_id = new_request()
    expiration = (datetime.now(timezone(timedelta(hours=-3))) + timedelta(minutes=10)).replace(microsecond=0)
    result = expect(client.post(f"/admin/keys/requests/{request_id}/approve", headers=world["owner"]["headers"], json={"expires_at": expiration.isoformat()}))
    key = expect(client.get(f'/digital_key?key_id={result["digital_key_id"]}', headers=world["visitor"]["headers"]))
    assert struct.unpack(">QQQQ", bytes.fromhex(key["payload"])[:32])[3] == int(expiration.timestamp())


def test_no_secret_in_catalog_or_admin(client, world):
    for path in ("/digital_lock/all", f'/digital_lock?room_id={world["owner"]["room"]}', "/admin/locks", "/admin/keys/requests", "/admin/key-holders"):
        no_secret(expect(client.get(path, headers=world["owner"]["headers"])))


@pytest.mark.parametrize("path", ["/digital_key/new", "/digital_key/use", "/admin/keys/issue", "/digital_lock/new"])
def test_legacy_paths_cannot_bypass_decision(client, world, path):
    assert client.post(path, json={}).status_code in (401, 403, 404, 410, 422)
    response = client.post(path, headers=world["visitor"]["headers"], json={"user_id": world["visitor"]["id"], "lock_id": world["owner"]["lock"], "room_id": world["owner"]["room"]})
    assert response.status_code in (403, 404, 410)


def test_delete_empty_hierarchy(client, world):
    headers = world["owner"]["headers"]
    institution = expect(client.post("/admin/institutions", headers=headers, json={"name": "Temporária " + uuid.uuid4().hex}))["institution_id"]
    building = expect(client.post("/admin/buildings", headers=headers, json={**world["owner"]["building_data"], "institution_id": institution}))["building_id"]
    room = expect(client.post("/admin/rooms", headers=headers, json={"building_id": building, "name": "Temporária", "number": "2"}))["room_id"]
    lock = expect(client.post("/admin/locks", headers=headers, json={"room_id": room}))["digital_lock_id"]
    for entity, resource_id in (("locks", lock), ("rooms", room), ("buildings", building), ("institutions", institution)):
        expect(client.delete(f"/admin/{entity}/{resource_id}", headers=headers))
