import os
import uuid

import pytest

if os.getenv("FLIKE_TEST_DATABASE") != "1" or os.getenv("DB_DATABASE") != "flike_test":
    raise RuntimeError("Use ./scripts/demo.sh test: these tests require the isolated flike_test database.")

from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app, raise_server_exceptions=False) as value:
        yield value


def expect(response, status=200):
    assert response.status_code == status, (response.status_code, response.text)
    return response.json()


@pytest.fixture(scope="session")
def world(client):
    marker = uuid.uuid4().hex[:12]
    result = {"marker": marker, "password": "Demo-Segura-123!"}
    for role in ("owner", "other", "visitor"):
        email = f"{role}-{marker}@example.com"
        user = expect(client.post("/user/new", json={"name": role, "email": email, "password": result["password"]}))
        token = expect(client.post("/auth/user", json={"email": email, "password": result["password"]}))["token"]
        result[role] = {"id": user["user_id"], "email": email, "headers": {"Authorization": f"Bearer {token}"}}
    for role in ("owner", "other"):
        actor = result[role]
        headers = actor["headers"]
        institution = expect(client.post("/admin/institutions", headers=headers, json={"name": f"Instituição {role} {marker}"}))
        actor["institution"] = institution["institution_id"]
        building_data = {
            "institution_id": actor["institution"], "name": "Edifício teste",
            "address_line_1": "Rua teste", "address_line_2": "", "city": "São Paulo",
            "state": "SP", "zip_code": "01000-000", "country": "Brasil",
        }
        actor["building_data"] = building_data
        actor["building"] = expect(client.post("/admin/buildings", headers=headers, json=building_data))["building_id"]
        actor["room"] = expect(client.post("/admin/rooms", headers=headers, json={"building_id": actor["building"], "name": "Sala teste", "number": "101"}))["room_id"]
        actor["lock"] = expect(client.post("/admin/locks", headers=headers, json={"room_id": actor["room"]}))["digital_lock_id"]
    return result


@pytest.fixture
def new_request(client, world):
    def create(actor="visitor", destination="owner"):
        return expect(client.post("/digital_key/request", headers=world[actor]["headers"], json={"lock_id": world[destination]["lock"]}))["request_id"]
    return create
