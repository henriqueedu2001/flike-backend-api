from datetime import datetime
from typing import *
from app.database.database_manager import Database
from app.modules.auth.hashes import secure_hash
from app.modules.auth.salt_gen import generate_salt

class UserNotFound(Exception):
    pass


class EmailAlreadyInUse(Exception):
    pass


class Repository:
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
    
    # def create_work(self, title: str, date: datetime, category: str, synopsis: str, edition_number: int, idiom: str, isbn: str, pages_num: int, tags: List[str], filenames: Dict):
    #     # creating the work entity in the work table
    #     create_work_query = """
    #         INSERT INTO work(title, date, category)
    #         VALUES(%s, %s, %s)
    #     """

    #     self.db.execute(create_work_query, (title, date, category))
    #     work_id = self.db.cursor.lastrowid

    #     # creating the edition in the edition table
    #     create_edition_query = """
    #         INSERT INTO edition(work_id, edition_number, idiom, title, date, synopsis,  isbn, pages_num, views, likes, shares)
    #         VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    #     """
        
    #     work_id
    #     if not edition_number: edition_number = 1
    #     if not idiom: idiom = 'PT-BR'
    #     if not isbn: isbn = None
    #     views, likes, shares = 0, 0, 0
        
    #     self.db.execute(create_edition_query, (work_id, edition_number, idiom, title, date, synopsis, isbn, pages_num, views, likes, shares))
    #     edition_id = self.db.cursor.lastrowid

    #     # creating the tags in the tags table
    #     create_tags_query = """
    #         INSERT INTO tags(work_id, tag_name)
    #         VALUES(%s, %s)
    #     """

    #     tags = [(work_id, tag) for tag in tags]

    #     self.db.execute_many(create_tags_query, tags)

    #     # saving the file paths in the database
    #     create_files_query = """
    #         INSERT INTO files(work_id, edition_id, filepath, category)
    #         VALUES(%s, %s, %s, %s)
    #     """

    #     for key, value in filenames.items():
    #         filepath = value
    #         file_category = key
    #         if filepath is not None:
    #             self.db.execute(create_files_query, (work_id, edition_id, filepath, file_category))

    #     # committing to the database       
    #     self.db.commit()

    #     return work_id, edition_id
    

    # def get_all_work_cards(self):
    #     get_all_works_query = """
    #         SELECT * FROM work
    #     """
    #     self.db.execute(get_all_works_query)
    #     works = self.db.fetch_all()
    #     return works