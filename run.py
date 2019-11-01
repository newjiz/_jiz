import os
import logging

from random import choices
from datetime import datetime
from dotenv import load_dotenv
from flask_cors import CORS

from flask import Flask, request

from pymongo import MongoClient, UpdateOne
from bson.json_util import dumps
from bson.objectid import ObjectId

from elo import update_elo, R0
from utils import ok, error

load_dotenv()
db = None
log = logging.getLogger(__name__)

app = Flask(__name__)
cors = CORS(app)


@app.route("/", methods=["GET"])
def index(): 
    return ok()


@app.route("/user/<id>", methods=["GET"])
def get_user(id):
    """
    Get a users data (profile).

    Path parameters
    ---------------
        id: str
            The id of the user.

    Response codes
    --------------
        200
            The user data.

        400
            If the id is not valid.

        404
            If the content is not found.
    """

    try:
        user_id = ObjectId(id)
    except Exception as e:
        return error("{}".format(e), 400)
    
    _user = db.users.find_one({"_id": user_id})
    
    if _user is None:
        return error("User not found", 404)        

    return dumps({"data": _user}), 200


@app.route("/content", methods=["get"])
def content_all():
    """
    Get all content.

    Response codes
    --------------
        200
            All content.

        500
            Could not get all content.
    """

    try:
        content = db.content.find()

    except Exception as e:
        log.error(e)
        return error(message=str(e), code=500)

    return dumps({"data": content}), 200


@app.route("/content/<id>", methods=["get"])
def content_get(id):
    """
    Get a content by id.

    Path parameters
    ---------------
        id: str
            The id of the content.

    Response codes
    --------------
        200
            The content.

        400
            If the id is not valid.

        404
            If the content is not found.
    """

    try:
        _id = ObjectId(id)
    except Exception as e:
        return error(f"Raised exception: {e}", 400)

    content = db.content.find_one({"_id": _id})

    if content is None:
        return error("Content not found", 404)

    return dumps({"data": content}), 200


@app.route("/content/user/<id>", methods=["get"])
def get_user_content(id):
    """
    Get a users content.

    Path parameters
    ---------------
        id: str
            The id of the user.

    Response codes
    --------------
        200
            The given users content.

        400
            If the id is not valid.

        404
            If the user is not found.
    """

    try:
        user_id = ObjectId(id)
    except Exception as e:
        return error("{}".format(e), 400)

    _c = db.content.find({"user_id": user_id})
    
    if _c is None:
        return error("Content not found", 404)

    return dumps({"data": _c}), 200


@app.route("/content", methods=["post"])
def content_post():
    """
    Create a content.

    JSON body
    ---------
        user_id: str
            The id of the user.

        content: str
            The content text

    Response codes
    --------------
        200
            The content created.

        400
            Bad request.

        404
            If the user is not found.
    """

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
            "user_id": ObjectId(data["user_id"]),
            "content": {
                "data": data["content"],
                "type": "text",
                "url": ""
            },
            "created": datetime.now(),
            "votes": {
                "total": 0,
                "up": 0,
                "down": 0,
                "elo": R0
            }
        }

        content_id = db.content.insert_one(content).inserted_id

    except Exception as e:
        log.error(e)
        return error(f"Raised exception: {e}", 400)

    return {"message": f"Content uploaded: {content_id}"}, 200


@app.route("/ranking", methods=["get"])
def ranking():
    """
    Returns the ranking (ELO based)

    Response codes
    --------------
        200
            Ranking list, ordered desc.
    """

    ranking = db.content.find().sort("votes.elo", -1)

    return dumps({"data": [r for r in ranking]}), 200


@app.route("/ranking2", methods=["get"])
def ranking2():
    """
    Returns the ranking (vote based)

    Response codes
    --------------
        200
            Ranking list, ordered desc.
    """

    ranking = db.content.aggregate([
            {
                "$match": {"votes.total": {"$gt": 0}}
            },
            {
                "$project": {
                    "_id": 1,
                    "score_p": {
                        "$divide": [
                            "$votes.up",
                            "$votes.total"
                            ]
                        },
                    "score_v": {"$subtract": ["$votes.up", "$votes.down"]}
                }
            },
            {
                "$sort": {"score_p": -1}
            }
        ])

    return dumps({"data": [r for r in ranking]}), 200



@app.route("/stack/<id>", methods=["get"])
def get_user_stack(id):
    """
    Get a users stack.

    Url parameters
    --------------
        id: str
            The id of the user.

    Response code
    -------------
        200
            The stack.

        400
            If the id is not valid.

        404
            If the user is not found.
    """

    try:
        user_id = ObjectId(id)
    except Exception as e:
        return error("{}".format(e), 400)

    user = db.user.find({"_id": user_id})
    
    if user is None:
        return error("User not found", 404)

    content = db.content.aggregate([
            {"$match": {"user_id": {"$ne": user_id}}},
            {"$sample": {"size": 2}}
        ])

    return dumps({"data": [c for c in content]}), 200


@app.route("/vote", methods=["post"])
def vote_content():
    """
    Vote a content.

    Url parameters
    --------------
        id: str
            The id of the user.

        w: str
            The id of the selected content (winner).

        l: str
            The id of the discarted content (loser).

    Response code
    -------------
        200
            Vote has been registered.

        400
            Bad request.

        401
            Vote not permitted (autovote).

        404
            If any object is not found.
    """

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


    if "win" not in data.keys():
        return error("No 'win' key", 400)

    try:
        win = db.content.find_one({"_id": ObjectId(data["win"])})

        if win is None:
            return error(f"Content {data['win']} not found", 404)

    except Exception as e:
        log.error(e)
        return error(f"Raised exception: {e}", 400) 
        

    if "los" not in data.keys():
        return error("No 'los' key", 400)

    try:
        los = db.content.find_one({"_id": ObjectId(data["los"])})

        if los is None:
            return error(f"User {data['los']} not found'", 404)

    except Exception as e:
        log.error(e)
        return error(f"Raised exception: {e}", 400)    

    if win["user_id"] == user["_id"] or los["user_id"] == user["_id"]:
        return error("No autovotes permited", 401)    

    if win is los:
        return error("Winner and looser should be different", 400)    

    query_win, query_los = update_elo(win, los)
    
    update = db.content.bulk_write([
            UpdateOne(query_win[0], query_win[1]),
            UpdateOne(query_los[0], query_los[1])
        ])

    log.info(update.bulk_api_result)

    return ok(f"Vote registered: {update.bulk_api_result['nModified']} contents modified.")


if __name__ == "__main__":
    mongo = MongoClient(
        os.environ["MONGO_HOST"],
        int(os.environ["MONGO_PORT"])
        )
    
    db = mongo.jiz
    app.run(host="0.0.0.0", port=5000, debug=True)
