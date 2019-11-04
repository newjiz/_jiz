import logging

from os import environ

from dotenv import load_dotenv
from pymongo import MongoClient


load_dotenv()

JWT_SECRET = environ["JWT_SECRET"]
JWT_ALG = environ["JWT_ALG"]

HOST = environ["HOST"]
PORT = environ["PORT"]

DEBUG = environ["DEBUG"]
LOGGER = logging.getLogger(__name__)

if bool(environ["LOCAL"]):
	mongo = MongoClient(environ["MONGO_HOST"], int(environ["MONGO_PORT"]))
	DB = mongo.jiz

else:
	mongo = MongoClient(environ["MONGO_URI"])
	DB = mongo.jiz