"""Additional data-integrity checks in the explicitly isolated test database."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
import subprocess
import uuid

import jwt
import os
import pytest
from mysql.connector.errors import IntegrityError

from app.database.database_manager import Database
from scripts.create_db import IncompatibleSchemaError, validate_existing_schema
from conftest import expect


def test_concurrent_signup_has_one_identity(client):
    email = f'concurrent-{uuid.uuid4().hex}@example.com'
    body = {'name': 'Concurrent signup', 'email': email, 'password': 'Teste-Seguro-123!'}
    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(lambda _: client.post('/user/new', json=body).status_code, range(2)))
    assert sorted(statuses) == [200, 409]
    expect(client.post('/auth/user', json={'email': email.upper(), 'password': body['password']}))


def test_failed_signup_rolls_back_personal_record(client, monkeypatch):
    email = f'rollback-{uuid.uuid4().hex}@example.com'
    body = {'name': 'Rollback signup', 'email': email, 'password': 'Teste-Seguro-123!'}
    original = Database.execute
    def fail_credentials(self, sql, params=None):
        if 'INSERT INTO auth' in sql:
            raise RuntimeError('injected credential failure')
        return original(self, sql, params)
    with monkeypatch.context() as context:
        context.setattr(Database, 'execute', fail_credentials)
        assert client.post('/user/new', json=body).status_code == 500
    # A successful retry proves the failed transaction did not retain the e-mail.
    expect(client.post('/user/new', json=body))
    expect(client.post('/auth/user', json={'email': email, 'password': body['password']}))


@pytest.mark.parametrize('claims', [
    {'user_id': 1}, {'exp': 4102444800}, {'user_id': '1', 'exp': 4102444800},
    {'user_id': -1, 'exp': 4102444800}, {'user_id': True, 'exp': 4102444800},
    {'user_id': 2147483647, 'exp': 4102444800},
])
def test_invalid_identity_claims_rejected(client, claims):
    token = jwt.encode(claims, os.environ['JWT_SECRET'], algorithm='HS256')
    expect(client.get('/user/me', headers={'Authorization': f'Bearer {token}'}), 401)


def test_migration_preserves_legacy_key_and_enforces_unique_request():
    """Replay original DDL with private table names; do not replace live/test tables."""
    db = Database()
    db.execute('SELECT DATABASE() AS name')
    assert db.fetch_one()['name'] == 'flike_test'
    prefix = 'migration_' + uuid.uuid4().hex[:10] + '_'
    names = ('auth', 'user', 'institution', 'building', 'room', 'digital_lock', 'digital_key', 'digital_key_request', 'event_log')
    replacement = re.compile(r'\b(' + '|'.join(names) + r')\b')
    def isolated(sql):
        value = replacement.sub(lambda match: prefix + match[0], sql)
        return value.replace('fk_digital_key_request', prefix + 'fk_request')
    root = Path(__file__).resolve().parents[1]
    source = subprocess.check_output(['git', 'show', 'e9268cc:scripts/create_db.py'], cwd=root, text=True)
    statements = re.findall(r'CREATE TABLE IF NOT EXISTS .*?;', source, re.DOTALL)
    created = []
    try:
        with db.connection.cursor() as schema_cursor:
            assert validate_existing_schema(schema_cursor, prefix) is False
        for name, sql in zip(names, statements, strict=True):
            db.execute(isolated(sql))
            created.append(name)
            if name == 'auth':
                with db.connection.cursor() as schema_cursor:
                    with pytest.raises(IncompatibleSchemaError, match='tabelas ausentes'):
                        validate_existing_schema(schema_cursor, prefix)
        with db.connection.cursor() as schema_cursor:
            with pytest.raises(IncompatibleSchemaError) as legacy_error:
                validate_existing_schema(schema_cursor, prefix)
            assert 'request_id' in str(legacy_error.value)
            assert 'decided_at' in str(legacy_error.value)
            assert 'UNIQUE' in str(legacy_error.value)
            assert 'FK' in str(legacy_error.value)
        db.execute(isolated("INSERT INTO user(id,name,email) VALUES(1,'Legacy','legacy@example.com')"))
        db.execute(isolated("INSERT INTO institution(id,owner_id,name) VALUES(1,1,'Legacy')"))
        db.execute(isolated("INSERT INTO building(id,institution_id,name,address_line_1,city,state,zip_code,country) VALUES(1,1,'Legacy','Test','Test','Test','1','Test')"))
        db.execute(isolated("INSERT INTO room(id,building_id,name,number) VALUES(1,1,'Legacy','1')"))
        db.execute(isolated('INSERT INTO digital_lock(id,room_id,secret_key) VALUES(1,1,%s)'), (bytes(range(32)),))
        payload = bytes(range(48))
        db.execute(isolated('INSERT INTO digital_key(id,user_id,digital_lock_id,payload) VALUES(1,1,1,%s)'), (payload,))
        db.execute(isolated("INSERT INTO digital_key_request(id,user_id,digital_lock_id,status) VALUES(1,1,1,'approved')"))
        db.commit()
        migration = (root / 'migrations/001_request_key_integrity.sql').read_text()
        migration = '\n'.join(line for line in migration.splitlines() if not line.lstrip().startswith('--'))
        for statement in migration.split(';'):
            if statement.strip():
                db.execute(isolated(statement))
        with db.connection.cursor() as schema_cursor:
            assert validate_existing_schema(schema_cursor, prefix) is True
        db.execute(isolated('SELECT request_id,payload FROM digital_key WHERE id=1'))
        legacy = db.fetch_one()
        assert legacy['request_id'] is None
        assert legacy['payload'] == payload
        db.execute(isolated('INSERT INTO digital_key(request_id,user_id,digital_lock_id,payload) VALUES(1,1,1,%s)'), (payload,))
        with pytest.raises(IntegrityError) as duplicate:
            db.execute(isolated('INSERT INTO digital_key(request_id,user_id,digital_lock_id,payload) VALUES(1,1,1,%s)'), (payload,))
        assert duplicate.value.errno == 1062
        db.rollback()
        with pytest.raises(IntegrityError):
            db.execute(isolated('INSERT INTO digital_key(request_id,user_id,digital_lock_id,payload) VALUES(999,1,1,%s)'), (payload,))
        db.rollback()
    finally:
        # The migrated key now references requests, so drop keys before requests.
        for name in ('event_log', 'digital_key', 'digital_key_request', 'digital_lock', 'room', 'building', 'institution', 'user', 'auth'):
            if name in created:
                db.execute(f'DROP TABLE IF EXISTS {prefix}{name}')
        db.close()
