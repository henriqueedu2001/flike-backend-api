from datetime import datetime
from typing import *
from app.database.database_manager import Database
from app.modules.auth.hashes import secure_hash
from app.modules.auth.salt_gen import generate_salt

class UserNotFound(Exception):
    pass


class EmailAlreadyInUse(Exception):
    pass

class CredentialsDontExist(Exception):
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
    

class InstitutionRepository:
    def __init__(self, db: Database):
        self.db = db 


    def get_all_institutions(self):
        query = 'SELECT * FROM institution;'
        self.db.execute(query)
        institutions = self.db.fetch_all()
        return institutions
    

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