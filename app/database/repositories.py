from datetime import datetime
from typing import *
from mysql.connector.errors import IntegrityError
from app.database.database_manager import Database
from app.modules.auth.hashes import secure_hash
from app.modules.auth.salt_gen import generate_salt
from app.modules.cmac.key import *

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


class DigitalKeyAlreadyUsed(Exception):
    pass


class InvalidDigitalKeySignature(Exception):
    pass


class UserRepository:
    def __init__(self, db: Database):
        self.db = db 

    
    def create_user(self, name: str, email: str, password: str):
        # check if the email is new or already in use
        query = f'SELECT email FROM user WHERE email = %s;'
        self.db.execute(query, (email,))
        fetched_email = self.db.fetch_all()

        if fetched_email:
            raise EmailAlreadyInUse(f'email \"{fetched_email}\" already in use')
        
        # create user
        query = 'INSERT INTO user(name, email) VALUES(%s, %s);'
        self.db.execute(query, (name, email))

        # create credentials
        query = 'INSERT INTO auth(salt, hashed_email, hashed_password) VALUES(%s, %s, %s)'
        salt = generate_salt()
        hashed_email = secure_hash(email)
        hashed_password = secure_hash(salt + password)
        self.db.execute(query, (salt, hashed_email, hashed_password))

        # retrieving the user id
        query = 'SELECT id FROM user WHERE email = %s'
        self.db.execute(query, (email, ))
        user_id = self.db.fetch_one().get('id')

        # committing the transaction
        self.db.commit()

        return user_id

    
    def get_all_users(self):
        query = 'SELECT * FROM user;'
        self.db.execute(query)
        users = self.db.fetch_all()
        return users
    

    def get_user(self, user_id: int):
        query = f'SELECT * FROM user WHERE id = {user_id};'
        self.db.execute(query)
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
        # get the credentials and the salt from the email
        hashed_email = secure_hash(email)
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
        old_email = current_user.get('email')

        if email != old_email:
            query = 'SELECT email FROM user WHERE email = %s AND id != %s;'
            self.db.execute(query, (email, user_id))
            if self.db.fetch_all():
                raise EmailAlreadyInUse(f'email \"{email}\" already in use')

        query = 'UPDATE user SET name = %s, email = %s WHERE id = %s'
        self.db.execute(query, (name, email, user_id))

        if email != old_email:
            old_hashed_email = secure_hash(old_email)
            new_hashed_email = secure_hash(email)
            update_auth_query = 'UPDATE auth SET hashed_email = %s WHERE hashed_email = %s'
            self.db.execute(update_auth_query, (new_hashed_email, old_hashed_email))

        self.db.commit()
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
        self.db.cursor.execute(select_query, (institution_id,))
        row = self.db.cursor.fetchone()

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
        self.db.cursor.execute(select_query, (building_id,))
        row = self.db.cursor.fetchone()

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
        self.db.cursor.execute(select_query, (room_id,))
        row = self.db.cursor.fetchone()

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
        self.db.cursor.execute(select_query, (digital_lock_id,))
        row = self.db.cursor.fetchone()

        created_at = row.get('created_at')

        self.db.commit()
        return digital_lock_id, created_at


class DigitalKeyRepository:
    def __init__(self, db: Database):
        self.db = db
    

    def get_all_digital_keys(self):
        query = 'SELECT * FROM digital_key;'
        self.db.execute(query)
        digital_keys = self.db.fetch_all()
        return digital_keys


    def get_key_holders_by_room(self, room_id: int):
        query = """
            SELECT user.id AS user_id, user.name, user.email,
                   MAX(digital_key.used) AS used,
                   MAX(digital_key.used_at) AS used_at
            FROM digital_key
            JOIN digital_lock ON digital_key.digital_lock_id = digital_lock.id
            JOIN user ON digital_key.user_id = user.id
            WHERE digital_lock.room_id = %s
            GROUP BY user.id, user.name, user.email;
        """
        self.db.execute(query, (room_id,))
        return self.db.fetch_all()


    def get_key_holders_by_owner(self, owner_id: int):
        query = """
            SELECT user.id AS user_id, user.name, user.email,
                   MAX(digital_key.used) AS used,
                   MAX(digital_key.used_at) AS used_at
            FROM digital_key
            JOIN digital_lock ON digital_key.digital_lock_id = digital_lock.id
            JOIN room ON digital_lock.room_id = room.id
            JOIN building ON room.building_id = building.id
            JOIN institution ON building.institution_id = institution.id
            JOIN user ON digital_key.user_id = user.id
            WHERE institution.owner_id = %s
            GROUP BY user.id, user.name, user.email;
        """
        self.db.execute(query, (owner_id,))
        return self.db.fetch_all()


    def get_key_usage_history(self, owner_id: int, user_id: int):
        query = """
            SELECT digital_key.id AS key_id,
                   digital_key.used,
                   digital_key.used_at,
                   digital_key.expires_at,
                   digital_key.created_at,
                   room.id AS room_id,
                   room.name AS room_name,
                   building.id AS building_id,
                   building.name AS building_name
            FROM digital_key
            JOIN digital_lock ON digital_key.digital_lock_id = digital_lock.id
            JOIN room ON digital_lock.room_id = room.id
            JOIN building ON room.building_id = building.id
            JOIN institution ON building.institution_id = institution.id
            WHERE institution.owner_id = %s AND digital_key.user_id = %s
            ORDER BY digital_key.created_at DESC;
        """
        self.db.execute(query, (owner_id, user_id))
        return self.db.fetch_all()


    def get_digital_key(self, digital_key_id: int):
        query = 'SELECT * FROM digital_key WHERE id = %s;'
        self.db.execute(query, (digital_key_id,))
        digital_key = self.db.fetch_one()

        if not digital_key:
            raise DigitalKeyNotFound(f'digital_key with id = {digital_key_id} not found in the database')
        return digital_key


    def get_digital_key_by_payload(self, payload: bytes):
        query = 'SELECT * FROM digital_key WHERE payload = %s;'
        self.db.execute(query, (payload,))
        digital_key = self.db.fetch_one()

        if not digital_key:
            raise DigitalKeyNotFound('digital_key with the given payload not found in the database')
        return digital_key


    def use_digital_key(self, payload: bytes):
        digital_key = self.get_digital_key_by_payload(payload)

        if digital_key['used']:
            raise DigitalKeyAlreadyUsed(f"digital_key with id = {digital_key['id']} has already been used")

        lock_query = 'SELECT secret_key FROM digital_lock WHERE id = %s;'
        self.db.execute(lock_query, (digital_key['digital_lock_id'],))
        lock_row = self.db.fetch_one()

        if not lock_row:
            raise DigitalLockNotFound(f"digital_lock with id = {digital_key['digital_lock_id']} not found in the database")

        secret_key = lock_row.get('secret_key')
        if not AES_CMAC.validate_signature(payload, Key(secret_key)):
            raise InvalidDigitalKeySignature('digital_key signature is invalid')

        used_at = datetime.now()
        update_query = 'UPDATE digital_key SET used = TRUE, used_at = %s WHERE id = %s;'
        self.db.execute(update_query, (used_at, digital_key['id']))
        self.db.commit()
        return digital_key['id'], used_at


    def get_digital_keys_by_user(self, user_id: int):
        query = 'SELECT * FROM digital_key WHERE user_id = %s;'
        self.db.execute(query, (user_id,))
        return self.db.fetch_all()


    def create_digital_key(self, user_id: int, digital_lock_id: int, expiration: datetime):
        query = 'SELECT secret_key from digital_lock WHERE id = %s'
        self.db.execute(query, (digital_lock_id, ))
        row = self.db.cursor.fetchone()

        if not row:
            raise DigitalLockNotFound(f'digital_lock with id = {digital_lock_id} not found in the database')
        secret_key = row.get('secret_key')

        digital_key = DigitalKey(
            user_id=user_id,
            digital_lock_id=digital_lock_id,
            timestamp=datetime.now(),
            expiration=expiration,
            private_key=Key(secret_key)
        )

        payload = digital_key.payload

        query = 'INSERT INTO digital_key(user_id, digital_lock_id, payload, expires_at) VALUES(%s, %s, %s, %s)'
        self.db.execute(query, (user_id, digital_lock_id, payload, expiration))

        # retrieving the digital_lock_id
        digital_key_id = self.db.cursor.lastrowid

        # recovering the timestamp
        select_query = 'SELECT created_at FROM digital_key WHERE id = %s'
        self.db.cursor.execute(select_query, (digital_key_id,))
        row = self.db.cursor.fetchone()

        created_at = row.get('created_at')

        self.db.commit()
        return digital_key_id, created_at


class DigitalKeyRequestRepository:
    def __init__(self, db: Database):
        self.db = db


    def create_request(self, user_id: int, digital_lock_id: int) -> Tuple[int, datetime]:
        query = 'INSERT INTO digital_key_request(user_id, digital_lock_id) VALUES(%s, %s)'
        self.db.execute(query, (user_id, digital_lock_id))

        request_id = self.db.cursor.lastrowid

        select_query = 'SELECT created_at FROM digital_key_request WHERE id = %s'
        self.db.cursor.execute(select_query, (request_id,))
        row = self.db.cursor.fetchone()

        created_at = row.get('created_at')

        self.db.commit()
        return request_id, created_at


    def get_all_requests(self, status: Optional[str] = None):
        if status is not None:
            query = 'SELECT * FROM digital_key_request WHERE status = %s;'
            self.db.execute(query, (status,))
        else:
            query = 'SELECT * FROM digital_key_request;'
            self.db.execute(query)
        return self.db.fetch_all()


    def get_requests_by_owner(self, owner_id: int, status: Optional[str] = None):
        query = """
            SELECT digital_key_request.*
            FROM digital_key_request
            JOIN digital_lock ON digital_key_request.digital_lock_id = digital_lock.id
            JOIN room ON digital_lock.room_id = room.id
            JOIN building ON room.building_id = building.id
            JOIN institution ON building.institution_id = institution.id
            WHERE institution.owner_id = %s
        """
        params = [owner_id]
        if status is not None:
            query += ' AND digital_key_request.status = %s'
            params.append(status)
        query += ';'
        self.db.execute(query, tuple(params))
        return self.db.fetch_all()


    def get_request(self, request_id: int):
        query = 'SELECT * FROM digital_key_request WHERE id = %s;'
        self.db.execute(query, (request_id,))
        request = self.db.fetch_one()

        if not request:
            raise DigitalKeyRequestNotFound(f'digital_key_request with id = {request_id} not found in the database')
        return request


    def update_status(self, request_id: int, status: str):
        self.get_request(request_id)

        query = 'UPDATE digital_key_request SET status = %s WHERE id = %s'
        self.db.execute(query, (status, request_id))
        self.db.commit()
        return self.get_request(request_id)