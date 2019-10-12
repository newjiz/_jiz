import os
import logging

from random import choices
from datetime import datetime
from dotenv import load_dotenv
from flask_cors import CORS

from flask import Flask, request

from pymongo import MongoClient
from bson.json_util import dumps
from bson.objectid import ObjectId

load_dotenv()
db = None
log = logging.getLogger(__name__)

app = Flask(__name__)
cors = CORS(app)


def ok(message="Ok", code=200):
    return {"message": message}, code

def error(message="Bad request", code=400):
    return {"message": message}, code


@app.route("/", methods=["GET"])
def index(): 
    return ok()

@app.route("/user/<id>", methods=["GET"])
def get_user(id):
    try:
        user_id = ObjectId(id)
    except Exception as e:
        return error("{}".format(e), 400)
    
    _user = db.users.find_one({"_id": user_id})
    
    if _user is None:
        return error("User not found", 404)        

    return dumps({"data": _user}), 200


@app.route("/user/<id>/content", methods=["get"])
def get_user_content(id):
    try:
        user_id = ObjectId(id)
    except Exception as e:
        return error("{}".format(e), 400)

    _c = db.content.find({"user_id": user_id})
    
    if _c is None:
        return error("Content not found", 404)

    return dumps({"data": _c}), 200


@app.route("/content/<id>", methods=["get"])
def content_get(id):
    try:
        _id = ObjectId(id)
    except Exception as e:
        return error(f"Raised exception: {e}", 400)

    content = db.content.find_one({"_id": _id})

    if content is None:
        return error("Content not found", 404)

    return dumps({"data": content}), 200


@app.route("/content", methods=["post"])
def content_post():
    data = request.json
    
    if "user_id" not in data.keys():
        return error("No 'user_id' key", 400)

    try:
        user = db.users.find_one({"_id": ObjectId(data["user_id"])})

        if user is None:
            return error(f"User {data['user_id']} not found'", 404)

    except Exception as e:
        log.error(e)
        return error(f"Raised exception: {e}", 400)

    try:
        _c = db.content.find_one({"user_id": user["_id"]}) 

        if _c is not None:
            return error("Content already exists", 400)

    except Exception as e:
        log.error(e)
        return error(f"Raised exception: {e}", 400)

    try:
        content = {
            "user_id": data["user_id"],
            "content": {
                "data": data["content"],
                "type": "text",
                "url": ""
            },
            "created": datetime.now(),
            "votes": {
                "up": 0,
                "down": 0
            }
        }

        content_id = db.content.insert_one(content).inserted_id

    except Exception as e:
        log.error(e)
        return error(f"Raised exception: {e}", 400)

    return {"message": f"Content uploaded: {content_id}"}, 200

"""
TODO
"""

@app.route("/ranking", methods=["get"])
def ranking():
    content = db.content.find()
    return dumps({"data": content}), 200


@app.route("/stack/<id>", methods=["get"])
def get_user_stack(id):
    return ok()


@app.route("/vote", methods=["post"])
def vote_content():
    """
    0: -1 (++down)
    1: +1 (++up)
    2: no action
    """
    valid_votes = [0, 1, 2]

    return ok()


if __name__ == "__main__":
    mongo = MongoClient(
        os.environ["MONGO_HOST"],
        int(os.environ["MONGO_PORT"])
        )
    
    db = mongo.jiz

    app.run(host="0.0.0.0", port=5000, debug=True)
