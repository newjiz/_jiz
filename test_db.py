from random import choice
from string import ascii_lowercase as letters

from datetime import datetime
from time import time

from os import environ
from dotenv import load_dotenv

from pymongo import MongoClient
from bson.objectid import ObjectId


def random_str(length=8):
    return "".join(choice(letters) for _ in range(length))


class TestDB:
    contest = None
    users = {}
    content = {}

    N = 0

    def __init__(self, n=100):
        # Load the database

        load_dotenv()

        if bool(environ["LOCAL"]):
            mongo = MongoClient(environ["MONGO_HOST"], int(environ["MONGO_PORT"]))
            self.db = mongo.jiz

        else:
            mongo = MongoClient(environ["MONGO_URI"])
            self.db = mongo.jiz

        self.N = n
        print(f"Number of users: {self.N}")

        # Create test collections

        self.create_collections()


        # Create dummy data
        t = time()
        
        self.create_contest()

        for _ in range(self.N):
            try:
                self.create_user()
            except Exception as e:
                print(f"Could not create user: {e}")
        

        for _, u in self.users.items():
            try:
                self.create_content(u["_id"])
            except Exception as e:
                print(f"{u['_id']}: {e}")

        t = time() - t
        print(f"Data creation time: {t:2.6} s.")


        # Delete the test collections

        self.purge()


    def create_collections(self):
        try:
            self.db.create_collection("test_contest")
        except Exception:
            pass
        
        try:
            self.db.create_collection("test_users")
        except Exception:
            pass
        
        try:
            self.db.create_collection("test_content")
        except Exception:
            pass

        try:
            self.db.create_collection("test_votes")
        except Exception:
            pass


    def create_contest(self):
        contest_id = self.db.test_contest.insert_one({
            "title": random_str(),
            "description": random_str(),
            "prize": random_str(),
            "content": {
                "type": "text",
                "max": 100
            },
            "current": True,
            "test": True
        }).inserted_id

        self.contest = self.db.test_contest.find_one({"_id": contest_id})
        print(f"Contest created: {contest_id}")


    def create_user(self):
        user_id = self.db.test_users.insert_one({
            "username": random_str(),
            "email": random_str(),
            "description": random_str(),
            "password": random_str(),
            "test": True
        }).inserted_id

        self.users[str(user_id)] = self.db.test_users.find_one({"_id": user_id})
        # print(f"User created: {user_id}")


    def create_content(self, user_id):
        content_id = self.db.test_content.insert_one({
            "user_id": user_id,
            "content": {
                "data": " ".join(random_str() for _ in range(12))
            },
            "created": datetime.now(),
            "contest": self.contest["_id"],
            "votes": {
                "elo": 1500,
                "up": 0,
                "down": 0,
                "total": 0
            },
            "test": True
        }).inserted_id

        self.content[str(content_id)] = self.db.test_content.find_one({"_id": content_id})
        # print(f"Content created: {content_id}")

    def vote(self, user_id, win, los):
        pass

    def purge(self):
        print("Purging all test data.")

        print("Contest...", end="")
        self.db.drop_collection("test_contest")
        print("done.")

        print("Users...", end="")
        self.db.drop_collection("test_users")
        print("done.")

        print("Content...", end="")
        self.db.drop_collection("test_content")
        print("done.")

        print("Votes...", end="")
        self.db.drop_collection("test_votes")
        print("done.")

if __name__ == "__main__":
    TestDB(10)

