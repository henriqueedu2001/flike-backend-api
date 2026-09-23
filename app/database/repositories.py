from datetime import datetime, timedelta
from typing import *
from mysql.connector.errors import IntegrityError
from app.database.database_manager import Database
from app.modules.auth.hashes import secure_hash
from app.modules.auth.salt_gen import generate_salt
from app.modules.cmac.key import DigitalKey, Key
from app.services.time import utc_now, as_utc, database_time

class UserNotFound(Exception):
    pass


class ResourceInUse(Exception):
    pass


class EmailAlreadyInUse(Exception):
    pass

class CredentialsDontExist(Exception):
    pass


class WrongPassword(Exception):
    pass


class InstitutionNotFound(Exception):
    pass


class BuildingNotFound(Exception):
    pass


class RoomNotFound(Exception):
    pass


class DigitalLockNotFound(Exception):
    pass


class DigitalKeyNotFound(Exception):
    pass


class DigitalKeyRequestNotFound(Exception):
    pass


class UserRepository:
    def __init__(self, db: Database):
        self.db = db 

    
    def create_user(self, name: str, email: str, password: str):
        email = email.strip().lower()
        try:
            self.db.execute('INSERT INTO user(name, email) VALUES(%s, %s)', (name, email))
            user_id = self.db.cursor.lastrowid
            salt = generate_salt()
            self.db.execute(
                'INSERT INTO auth(salt, hashed_email, hashed_password) VALUES(%s, %s, %s)',
                (salt, secure_hash(email), secure_hash(salt + password)),
            )
            self.db.commit()
            return user_id
        except IntegrityError as error:
            self.db.rollback()
            if error.errno == 1062:
                raise EmailAlreadyInUse('Este e-mail já está cadastrado.') from None
            raise


    def get_all_users(self):
        query = 'SELECT * FROM user;'
        self.db.execute(query)
        users = self.db.fetch_all()
        return users
    

    def get_user(self, user_id: int):
        query = 'SELECT * FROM user WHERE id = %s;'
        self.db.execute(query, (user_id,))
        user = self.db.fetch_one()

        if not user:
            raise UserNotFound(f'user with id = {user_id} not found in the database')
        return user
    

    def get_user_from_email(self, email: str):
        query = 'SELECT * FROM user WHERE email = %s;'
        self.db.execute(query, (email, ))
        user = self.db.fetch_one()

        if not user:
            raise UserNotFound(f'user with email = {email} not found in the database')
        return user
    

    def authenticate_user(self, email: str, password: str):
        # Preserve login for legacy accounts whose stored e-mail used mixed case.
        try:
            stored_email = self.get_user_from_email(email)['email']
        except UserNotFound:
            raise CredentialsDontExist() from None
        hashed_email = secure_hash(stored_email)
        query = 'SELECT * FROM auth WHERE hashed_email = %s'
        self.db.execute(query, (hashed_email, ))
        credentials = self.db.fetch_one()

        # fail: no credentials in the database with that email
        if not credentials: raise CredentialsDontExist()

        # compares the hash(salt + informed password) with hash(salt + password)        
        salt = credentials.get('salt')
        hashed_password_credentials = credentials.get('hashed_password')
        hashed_password_informed = secure_hash(salt + password)

        # success: the hashes are equal
        if hashed_password_credentials == hashed_password_informed: return True

        return False


    def update_user(self, user_id: int, name: str, email: str):
        current_user = self.get_user(user_id)
        old_email = current_user['email']
        email = email.strip().lower()
        try:
            self.db.execute('UPDATE user SET name = %s, email = %s WHERE id = %s', (name, email, user_id))
            if email != old_email:
                self.db.execute(
                    'UPDATE auth SET hashed_email = %s WHERE hashed_email = %s',
                    (secure_hash(email), secure_hash(old_email)),
                )
            self.db.commit()
        except IntegrityError as error:
            self.db.rollback()
            if error.errno == 1062:
                raise EmailAlreadyInUse('Este e-mail já está cadastrado.') from None
            raise
        return self.get_user(user_id)


    def change_password(self, user_id: int, current_password: str, new_password: str):
        user = self.get_user(user_id)
        hashed_email = secure_hash(user.get('email'))

        query = 'SELECT * FROM auth WHERE hashed_email = %s'
        self.db.execute(query, (hashed_email, ))
        credentials = self.db.fetch_one()

        if not credentials: raise CredentialsDontExist()

        salt = credentials.get('salt')
        hashed_password_credentials = credentials.get('hashed_password')
        hashed_password_informed = secure_hash(salt + current_password)

        if hashed_password_credentials != hashed_password_informed:
            raise WrongPassword()

        new_hashed_password = secure_hash(salt + new_password)
        query = 'UPDATE auth SET hashed_password = %s WHERE hashed_email = %s'
        self.db.execute(query, (new_hashed_password, hashed_email))
        self.db.commit()
        return


class InstitutionRepository:
    def __init__(self, db: Database):
        self.db = db 


    def get_all_institutions(self):
        query = 'SELECT * FROM institution;'
        self.db.execute(query)
        institutions = self.db.fetch_all()
        return institutions


    def get_institutions_by_owner(self, owner_id: int):
        query = 'SELECT * FROM institution WHERE owner_id = %s;'
        self.db.execute(query, (owner_id,))
        return self.db.fetch_all()


    def get_institution(self, institution_id: int):
        query = 'SELECT * FROM institution WHERE id = %s;'
        self.db.execute(query, (institution_id,))
        institution = self.db.fetch_one()

        if not institution:
            raise InstitutionNotFound(f'institution with id = {institution_id} not found in the database')
        return institution


    def search_institutions(self, q: str):
        query = 'SELECT * FROM institution WHERE name LIKE %s;'
        self.db.execute(query, (f'%{q}%',))
        return self.db.fetch_all()


    def update_institution(self, institution_id: int, name: str):
        self.get_institution(institution_id)

        query = 'UPDATE institution SET name = %s WHERE id = %s'
        self.db.execute(query, (name, institution_id))
        self.db.commit()
        return self.get_institution(institution_id)


    def delete_institution(self, institution_id: int):
        self.get_institution(institution_id)

        query = 'DELETE FROM institution WHERE id = %s'
        try:
            self.db.execute(query, (institution_id,))
        except IntegrityError:
            self.db.rollback()
            raise ResourceInUse(f'institution with id = {institution_id} still has buildings attached to it')
        self.db.commit()
        return


    def create_institution(self, user_id: int, institution_name: str) -> Tuple[int, datetime]:
        query = """
            INSERT INTO institution(owner_id, name)
            VALUES(%s, %s)
        """
        # creating the institution
        self.db.execute(query, (user_id, institution_name))

        # retrieving the institution_id
        institution_id = self.db.cursor.lastrowid
        
        # recovering the timestamp
        select_query = 'SELECT created_at FROM institution WHERE id = %s'
        self.db.execute(select_query, (institution_id,))
        row = self.db.fetch_one()

        created_at = row.get('created_at')

        self.db.commit()
        return institution_id, created_at


class BuildingRepository:
    def __init__(self, db: Database):
        self.db = db
    

    def get_all_buildings(self):
        query = 'SELECT * FROM building;'
        self.db.execute(query)
        buildings = self.db.fetch_all()
        return buildings


    def get_buildings_by_owner(self, owner_id: int):
        query = """
            SELECT building.*
            FROM building
            JOIN institution ON building.institution_id = institution.id
            WHERE institution.owner_id = %s;
        """
        self.db.execute(query, (owner_id,))
        return self.db.fetch_all()


    def get_building(self, building_id: int):
        query = 'SELECT * FROM building WHERE id = %s;'
        self.db.execute(query, (building_id,))
        building = self.db.fetch_one()

        if not building:
            raise BuildingNotFound(f'building with id = {building_id} not found in the database')
        return building


    def get_owner_id(self, building_id: int) -> int:
        query = """
            SELECT institution.owner_id AS owner_id
            FROM building
            JOIN institution ON building.institution_id = institution.id
            WHERE building.id = %s;
        """
        self.db.execute(query, (building_id,))
        row = self.db.fetch_one()

        if not row:
            raise BuildingNotFound(f'building with id = {building_id} not found in the database')
        return row.get('owner_id')


    def search_buildings(self, q: str, institution_id: Optional[int] = None):
        if institution_id is not None:
            query = 'SELECT * FROM building WHERE name LIKE %s AND institution_id = %s;'
            self.db.execute(query, (f'%{q}%', institution_id))
        else:
            query = 'SELECT * FROM building WHERE name LIKE %s;'
            self.db.execute(query, (f'%{q}%',))
        return self.db.fetch_all()


    def update_building(
        self,
        building_id: int,
        institution_id: int,
        name: str,
        address_line_1: str,
        address_line_2: str,
        city: str,
        state: str,
        zip_code: str,
        country: str
    ):
        self.get_building(building_id)

        query = """
            UPDATE building
            SET institution_id = %s, name = %s, address_line_1 = %s, address_line_2 = %s,
                city = %s, state = %s, zip_code = %s, country = %s
            WHERE id = %s
        """
        self.db.execute(
            query,
            (institution_id, name, address_line_1, address_line_2, city, state, zip_code, country, building_id)
        )
        self.db.commit()
        return self.get_building(building_id)


    def delete_building(self, building_id: int):
        self.get_building(building_id)

        query = 'DELETE FROM building WHERE id = %s'
        try:
            self.db.execute(query, (building_id,))
        except IntegrityError:
            self.db.rollback()
            raise ResourceInUse(f'building with id = {building_id} still has rooms attached to it')
        self.db.commit()
        return


    def create_building(
        self,
        institution_id: int,
        name: str,
        address_line_1: str,
        address_line_2: str,
        city: str,
        state: str,
        zip_code: str,
        country: str
    ) -> Tuple[int, datetime]:
        query = """
            INSERT INTO building(
                institution_id,
                name,
                address_line_1,
                address_line_2,
                city,
                state,
                zip_code,
                country
            )
            VALUES(%s, %s, %s, %s, %s, %s, %s, %s)
        """
        # creating the institution
        self.db.execute(
            query, (
                institution_id,
                name,
                address_line_1,
                address_line_2,
                city,
                state,
                zip_code,
                country
            )
        )

        # retrieving the building_id
        building_id = self.db.cursor.lastrowid
        
        # recovering the timestamp
        select_query = 'SELECT created_at FROM building WHERE id = %s'
        self.db.execute(select_query, (building_id,))
        row = self.db.fetch_one()

        created_at = row.get('created_at')

        self.db.commit()
        return building_id, created_at


class RoomRepository:
    def __init__(self, db: Database):
        self.db = db
    

    def get_all_rooms(self):
        query = 'SELECT * FROM room;'
        self.db.execute(query)
        rooms = self.db.fetch_all()
        return rooms


    def get_rooms_by_owner(self, owner_id: int):
        query = """
            SELECT room.*
            FROM room
            JOIN building ON room.building_id = building.id
            JOIN institution ON building.institution_id = institution.id
            WHERE institution.owner_id = %s;
        """
        self.db.execute(query, (owner_id,))
        return self.db.fetch_all()


    def get_room(self, room_id: int):
        query = 'SELECT * FROM room WHERE id = %s;'
        self.db.execute(query, (room_id,))
        room = self.db.fetch_one()

        if not room:
            raise RoomNotFound(f'room with id = {room_id} not found in the database')
        return room


    def get_owner_id(self, room_id: int) -> int:
        query = """
            SELECT institution.owner_id AS owner_id
            FROM room
            JOIN building ON room.building_id = building.id
            JOIN institution ON building.institution_id = institution.id
            WHERE room.id = %s;
        """
        self.db.execute(query, (room_id,))
        row = self.db.fetch_one()

        if not row:
            raise RoomNotFound(f'room with id = {room_id} not found in the database')
        return row.get('owner_id')


    def search_rooms(self, q: str, building_id: Optional[int] = None):
        if building_id is not None:
            query = 'SELECT * FROM room WHERE (name LIKE %s OR number LIKE %s) AND building_id = %s;'
            self.db.execute(query, (f'%{q}%', f'%{q}%', building_id))
        else:
            query = 'SELECT * FROM room WHERE name LIKE %s OR number LIKE %s;'
            self.db.execute(query, (f'%{q}%', f'%{q}%'))
        return self.db.fetch_all()


    def update_room(self, room_id: int, building_id: int, name: str, number: str):
        self.get_room(room_id)

        query = 'UPDATE room SET building_id = %s, name = %s, number = %s WHERE id = %s'
        self.db.execute(query, (building_id, name, number, room_id))
        self.db.commit()
        return self.get_room(room_id)


    def delete_room(self, room_id: int):
        self.get_room(room_id)

        query = 'DELETE FROM room WHERE id = %s'
        try:
            self.db.execute(query, (room_id,))
        except IntegrityError:
            self.db.rollback()
            raise ResourceInUse(f'room with id = {room_id} still has digital locks attached to it')
        self.db.commit()
        return


    def create_room(
        self,
        building_id: str,
        name: str,
        number: str,
    ) -> Tuple[int, datetime]:
        query = 'INSERT INTO room(building_id, name, number) VALUES(%s, %s, %s)'

        # creating the room
        self.db.execute(query, (building_id, name, number))

        # retrieving the building_id
        room_id = self.db.cursor.lastrowid
        
        # recovering the timestamp
        select_query = 'SELECT created_at FROM room WHERE id = %s'
        self.db.execute(select_query, (room_id,))
        row = self.db.fetch_one()

        created_at = row.get('created_at')

        self.db.commit()
        return room_id, created_at


class DigitalLockRepository:
    def __init__(self, db: Database):
        self.db = db
    

    def get_all_digital_locks(self):
        query = 'SELECT * FROM digital_lock;'
        self.db.execute(query)
        digital_locks = self.db.fetch_all()
        return digital_locks


    def get_locks_by_owner(self, owner_id: int):
        query = """
            SELECT digital_lock.*
            FROM digital_lock
            JOIN room ON digital_lock.room_id = room.id
            JOIN building ON room.building_id = building.id
            JOIN institution ON building.institution_id = institution.id
            WHERE institution.owner_id = %s;
        """
        self.db.execute(query, (owner_id,))
        return self.db.fetch_all()


    def get_digital_lock(self, digital_lock_id: int):
        query = 'SELECT * FROM digital_lock WHERE id = %s;'
        self.db.execute(query, (digital_lock_id,))
        digital_lock = self.db.fetch_one()

        if not digital_lock:
            raise DigitalLockNotFound(f'digital_lock with id = {digital_lock_id} not found in the database')
        return digital_lock


    def get_locks_by_room(self, room_id: int):
        query = 'SELECT * FROM digital_lock WHERE room_id = %s;'
        self.db.execute(query, (room_id,))
        return self.db.fetch_all()


    def get_institution_owner(self, digital_lock_id: int) -> int:
        query = """
            SELECT institution.owner_id AS owner_id
            FROM digital_lock
            JOIN room ON digital_lock.room_id = room.id
            JOIN building ON room.building_id = building.id
            JOIN institution ON building.institution_id = institution.id
            WHERE digital_lock.id = %s
        """
        self.db.execute(query, (digital_lock_id,))
        row = self.db.fetch_one()

        if not row:
            raise DigitalLockNotFound(f'digital_lock with id = {digital_lock_id} not found in the database')
        return row.get('owner_id')


    def update_digital_lock(self, digital_lock_id: int, room_id: int):
        self.get_digital_lock(digital_lock_id)

        query = 'UPDATE digital_lock SET room_id = %s WHERE id = %s'
        self.db.execute(query, (room_id, digital_lock_id))
        self.db.commit()
        return self.get_digital_lock(digital_lock_id)


    def delete_digital_lock(self, digital_lock_id: int):
        self.get_digital_lock(digital_lock_id)

        query = 'DELETE FROM digital_lock WHERE id = %s'
        try:
            self.db.execute(query, (digital_lock_id,))
        except IntegrityError:
            self.db.rollback()
            raise ResourceInUse(
                f'digital_lock with id = {digital_lock_id} still has issued keys or key requests attached to it'
            )
        self.db.commit()
        return


    def create_digital_lock(self, room_id: int):
        query = 'INSERT INTO digital_lock(room_id, secret_key) VALUES(%s, %s)'
        secret_key = Key()

        # creating the room
        self.db.execute(query, (room_id, secret_key.key_value))

        # retrieving the digital_lock_id
        digital_lock_id = self.db.cursor.lastrowid
        
        # recovering the timestamp
        select_query = 'SELECT created_at FROM digital_lock WHERE id = %s'
        self.db.execute(select_query, (digital_lock_id,))
        row = self.db.fetch_one()

        created_at = row.get('created_at')

        self.db.commit()
        return digital_lock_id, created_at


class PermissionDenied(Exception):
    pass


class RequestAlreadyDecided(Exception):
    pass


class InvalidExpiration(Exception):
    pass


class DigitalKeyRepository:
    # Public projection intentionally excludes legacy consumption fields and secrets.
    SELECT_KEYS = """
        SELECT k.id, k.request_id, k.user_id, k.digital_lock_id, k.payload,
               k.created_at, k.created_at AS issued_at, k.expires_at,
               r.id AS room_id, r.name AS room_name,
               b.id AS building_id, b.name AS building_name,
               i.id AS institution_id, i.name AS institution_name
        FROM digital_key k
        JOIN digital_lock l ON k.digital_lock_id = l.id
        JOIN room r ON l.room_id = r.id
        JOIN building b ON r.building_id = b.id
        JOIN institution i ON b.institution_id = i.id
    """

    def __init__(self, db: Database):
        self.db = db

    def get_digital_key(self, digital_key_id: int):
        self.db.execute(self.SELECT_KEYS + ' WHERE k.id = %s', (digital_key_id,))
        key = self.db.fetch_one()
        if key is None:
            raise DigitalKeyNotFound('Chave digital não encontrada.')
        return key

    def get_digital_keys_by_user(self, user_id: int):
        self.db.execute(self.SELECT_KEYS + ' WHERE k.user_id = %s ORDER BY k.created_at DESC, k.id DESC', (user_id,))
        return self.db.fetch_all()

    def get_key_holders_by_room(self, room_id: int):
        self.db.execute("""
            SELECT u.id AS user_id, u.name, u.email, COUNT(*) AS key_count,
                   SUM(k.created_at <= UTC_TIMESTAMP() AND k.expires_at > UTC_TIMESTAMP()) AS active_key_count,
                   MAX(k.created_at) AS last_issued_at
            FROM digital_key k
            JOIN digital_lock l ON k.digital_lock_id = l.id
            JOIN user u ON k.user_id = u.id
            WHERE l.room_id = %s
            GROUP BY u.id, u.name, u.email ORDER BY u.name, u.id
        """, (room_id,))
        return self.db.fetch_all()

    def get_key_holders_by_owner(self, owner_id: int):
        self.db.execute("""
            SELECT u.id AS user_id, u.name, u.email, COUNT(*) AS key_count,
                   SUM(k.created_at <= UTC_TIMESTAMP() AND k.expires_at > UTC_TIMESTAMP()) AS active_key_count,
                   MAX(k.created_at) AS last_issued_at
            FROM digital_key k
            JOIN digital_lock l ON k.digital_lock_id = l.id
            JOIN room r ON l.room_id = r.id
            JOIN building b ON r.building_id = b.id
            JOIN institution i ON b.institution_id = i.id
            JOIN user u ON k.user_id = u.id
            WHERE i.owner_id = %s
            GROUP BY u.id, u.name, u.email ORDER BY u.name, u.id
        """, (owner_id,))
        return self.db.fetch_all()

    def get_key_usage_history(self, owner_id: int, user_id: int):
        # This is issuance history, not evidence of a physical door event.
        self.db.execute("""
            SELECT k.id AS key_id, k.request_id, k.user_id, k.digital_lock_id,
                   k.created_at, k.created_at AS issued_at, k.expires_at,
                   r.id AS room_id, r.name AS room_name,
                   b.id AS building_id, b.name AS building_name,
                   i.id AS institution_id, i.name AS institution_name
            FROM digital_key k
            JOIN digital_lock l ON k.digital_lock_id = l.id
            JOIN room r ON l.room_id = r.id
            JOIN building b ON r.building_id = b.id
            JOIN institution i ON b.institution_id = i.id
            WHERE i.owner_id = %s AND k.user_id = %s
            ORDER BY k.created_at DESC, k.id DESC
        """, (owner_id, user_id))
        return self.db.fetch_all()

    def create_digital_key(self, user_id: int, digital_lock_id: int, expiration: datetime,
                           *, request_id: int, issued_at: datetime):
        """Insert inside the caller's decision transaction; never commit here."""
        expiration = as_utc(expiration).replace(microsecond=0)
        issued_at = as_utc(issued_at).replace(microsecond=0)
        if expiration <= issued_at:
            raise InvalidExpiration('A expiração deve ser posterior à emissão.')
        self.db.execute('SELECT secret_key FROM digital_lock WHERE id = %s FOR SHARE', (digital_lock_id,))
        lock = self.db.fetch_one()
        if lock is None:
            raise DigitalLockNotFound('Tranca não encontrada.')
        key = DigitalKey(user_id, digital_lock_id, issued_at, expiration, Key(bytes(lock['secret_key'])))
        self.db.execute("""
            INSERT INTO digital_key(request_id, user_id, digital_lock_id, payload, created_at, expires_at)
            VALUES(%s, %s, %s, %s, %s, %s)
        """, (request_id, user_id, digital_lock_id, key.payload,
              database_time(issued_at), database_time(expiration)))
        return self.db.cursor.lastrowid, issued_at


class DigitalKeyRequestRepository:
    SELECT_REQUESTS = """
        SELECT q.id, q.user_id, q.digital_lock_id, q.status, q.created_at, q.decided_at,
               k.id AS digital_key_id,
               u.name AS user_name, u.email AS user_email,
               r.name AS room_name, b.name AS building_name, i.name AS institution_name
        FROM digital_key_request q
        JOIN user u ON q.user_id = u.id
        JOIN digital_lock l ON q.digital_lock_id = l.id
        JOIN room r ON l.room_id = r.id
        JOIN building b ON r.building_id = b.id
        JOIN institution i ON b.institution_id = i.id
        LEFT JOIN digital_key k ON k.request_id = q.id
    """

    def __init__(self, db: Database):
        self.db = db

    def create_request(self, user_id: int, digital_lock_id: int) -> Tuple[int, datetime]:
        DigitalLockRepository(self.db).get_digital_lock(digital_lock_id)
        created_at = utc_now()
        self.db.execute(
            'INSERT INTO digital_key_request(user_id, digital_lock_id, created_at) VALUES(%s, %s, %s)',
            (user_id, digital_lock_id, database_time(created_at)),
        )
        request_id = self.db.cursor.lastrowid
        self.db.commit()
        return request_id, created_at

    def _list(self, condition, identity, status):
        query = self.SELECT_REQUESTS + ' WHERE ' + condition
        params = [identity]
        if status is not None:
            query += ' AND q.status = %s'
            params.append(status)
        query += ' ORDER BY q.created_at DESC, q.id DESC'
        self.db.execute(query, tuple(params))
        return self.db.fetch_all()

    def get_requests_by_owner(self, owner_id: int, status: Optional[str] = None):
        return self._list('i.owner_id = %s', owner_id, status)

    def get_requests_by_user(self, user_id: int, status: Optional[str] = None):
        return self._list('q.user_id = %s', user_id, status)

    def get_request(self, request_id: int, *, for_update=False):
        self.db.execute('SELECT * FROM digital_key_request WHERE id = %s' + (' FOR UPDATE' if for_update else ''), (request_id,))
        request = self.db.fetch_one()
        if request is None:
            raise DigitalKeyRequestNotFound('Solicitação não encontrada.')
        return request

    def decide(self, request_id: int, owner_id: int, status: str, expiration=None):
        """Serialize decisions and commit the status and its unique key together."""
        if status not in ('approved', 'rejected'):
            raise ValueError('Invalid decision')
        try:
            request = self.get_request(request_id, for_update=True)
            actual_owner = DigitalLockRepository(self.db).get_institution_owner(request['digital_lock_id'])
            if actual_owner != owner_id:
                raise PermissionDenied('Somente o responsável pela instituição pode decidir este pedido.')
            if request['status'] != 'pending':
                raise RequestAlreadyDecided('Esta solicitação já foi decidida.')
            decided_at = utc_now()
            key_id = None
            if status == 'approved':
                expiration = expiration or decided_at + timedelta(hours=24)
                key_id, _ = DigitalKeyRepository(self.db).create_digital_key(
                    request['user_id'], request['digital_lock_id'], expiration,
                    request_id=request_id, issued_at=decided_at,
                )
            self.db.execute(
                'UPDATE digital_key_request SET status = %s, decided_at = %s WHERE id = %s',
                (status, database_time(decided_at), request_id),
            )
            self.db.commit()
            return key_id, decided_at
        except Exception:
            self.db.rollback()
            raise
