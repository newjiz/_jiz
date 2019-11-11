from datetime import datetime
from dotenv import load_dotenv

from flask_cors import CORS
from flask import Flask, request

from passlib.hash import pbkdf2_sha256

from pymongo import MongoClient, UpdateOne
from bson.json_util import dumps
from bson.objectid import ObjectId

from elo import update_elo, R0

from db_utils import *
from utils import *

from middleware import auth

from config import *

load_dotenv()
db = None
log = LOGGER

app = Flask(__name__)
cors = CORS(app)


# Open endpoints

@app.route("/register", methods=["post"])
def register():
    """
    Register a user.

    JSON Body
    ---------
        username: str
        email: str
        password: str
        description: str, optional

    Response codes
    --------------
        200
            JWT token

        400
            Bad request

        403
            Username exists
    """

    data = request.json

    if "username" not in data:
        return error(message="No 'username' given")

    # Check email + if it's valid

    if "email" not in data:
        return error(message="No 'email' given")

    if not valid_mail(data["email"]):
        return error(message="Email not valid")

    # Check password shit

    if "password" not in data:
        return error(message="No 'password' given")

    if len(data["password"]) < 8:
        return error(message="Password should be min. 8 char long")

    description = ""

    if "description" in data:
        description = data["description"]
    
    # username and email fields are unique 
    # for all users

    target_1 = db.users.find_one({"username": data["username"]})
    target_2 = db.users.find_one({"email": data["email"]})

    if (target_1 is not None) or (target_2 is not None):
        return error(message="User already exists", code=403)

    hashed_pass = pbkdf2_sha256.hash(data["password"], rounds=10**6, salt_size=2**4)

    new_user = {
        "username": data["username"],
        "email": data["email"],
        "password": hashed_pass,
        "description": description, 
        "created": datetime.now()
    }

    try:
        user_id = db.users.insert_one(new_user).inserted_id

    except Exception as e:
        log.error(e)
        return error("Could not register new user")

    data = {
        "token": encode({"user_id": str(user_id)})
        }

    return data, 200


@app.route("/login", methods=["post"])
def login():
    """
    Login a user.

    JSON Body
    ---------
        username: str
        password: str

    Response codes
    --------------
        200
            JWT token

        400
            Bad request

        404
            User not found
    """

    data = request.json

    if "username" not in data:
        return error(message="No 'username' given")

    if "password" not in data:
        return error(message="No 'password' given")

    if len(data["password"]) == 0:
        return error(message="Password is empty")
    
    target = db.users.find_one({"username": data["username"]})

    if target is None:
        return error(message="User not found", code=404) 


    if not pbkdf2_sha256.verify(data["password"], target["password"]):
        return error("Could not log in")

    data = {
        "token": encode({"user_id": str(target["_id"])})
        }

    return data, 200


@app.route("/user/<id>", methods=["get"])
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

    user = db_get_user({"user_id": id})    
    return dumps({"data": user}), 200


@app.route("/contest", methods=["get"])
def get_contest():
    """
    Get current contest

    Returns
    -------
        200
            Current contest
    """
    now = datetime.now()

    try:
        # contest = db.contest.find_one({"start": {"$lte": now}, "end": {"$gt": now}})
        contest = db.contest.find_one({"current": True})

    except Exception as e:
        log.error(e)
        return error()

    duration = contest["end"].timestamp() - contest["start"].timestamp()
    now = datetime.now().timestamp() - contest["start"].timestamp()
    contest["progress"] = now / duration

    return dumps({"data": contest})


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

@app.route("/content/contest/<id>", methods=["get"])
def get_contest_content(id):
    """
    Get a content by contest id.

    Path parameters
    ---------------
        id: str
            The id of the contest.

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

    content = db.content.find_one({"contest_id": _id})

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

    user = db_get_user({"user_id": id})

    _c = db.content.find({"user_id": user["_id"]})
    
    if _c is None:
        return error("Content not found", 404)

    return dumps({"data": _c}), 200

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

    data, pos = [], 1
    for r in ranking:
        data.append(r)
        data[pos-1]["position"] = pos
        pos += 1     

    return dumps({"data": data}), 200


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
                    "user_id": 1,
                    "created": 1,
                    "content": 1,
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


# Auth endpoints

@app.route("/", methods=["get"])
@auth
def index():
    user = db_get_user(request.jwt_data)

    try:
        content = db.content.find({"user_id": user["_id"]})
    except Exception:
        return error(message="User not found", code=404)

    return dumps({"data": {"user": user, "content": content}})


@app.route("/content", methods=["post"])
@auth
def content_post():
    """
    Create a content.

    Headers
    -------
        Authorization: str
            Users JWT token

    JSON body
    ---------
        contest_id: str
            Optional. The id of the contest.

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
    user = db_get_user(request.jwt_data)

    if "contest_id" not in data:
        contest = db.contest.find_one({"current": True})
        # return error(message="No 'contest_id' given")

    else:
        contest = db.contest.find_one({"_id": ObjectId(data["contest_id"])})

    if contest is None:
        return error(message="Contest not found", code=404)

    try:
        _c = db.content.find_one({"user_id": user["_id"], "contest_id": contest["_id"]}) 

        if _c is not None:
            return error("Content already exists", 400)

    except Exception as e:
        log.error(e)
        return error(f"Raised exception: {e}", 400)

    try:
        content = {
            "user_id": user["_id"],
            "content": {
                "data": data["content"],
                "type": "text",
                "url": ""
            },
            "contest_id": contest["_id"],
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

    return {"message": f"Content uploaded", "content_id": str(content_id)}, 200


@app.route("/stack", methods=["get"])
@auth
def get_user_stack():
    """
    Get a users stack.

    Headers
    -------
        Authorization: str
            JWT totken of the user.

    Response code
    -------------
        200
            The stack.

        400
            If the id is not valid.

        404
            If the user is not found.
    """

    user = db_get_user(request.jwt_data)

    content = db.content.aggregate([
            {"$match": {"user_id": {"$ne": user["_id"]}}},
            {"$sample": {"size": 2}}
        ])

    return dumps({"data": [c for c in content]}), 200


@app.route("/vote", methods=["post"])
@auth
def vote_content():
    """
    Vote a content.

    Headers
    -------
        Authorization: str
            JWT totken of the user.

    JSON Body
    ---------
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
    user = db_get_user(request.jwt_data)

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

    db.votes.insert_one({
        "user": user["_id"],
        "win": win["_id"],
        "los": los["_id"],
        "created": datetime.now() 
    })

    log.info(update.bulk_api_result)

    return ok(f"Vote registered: {update.bulk_api_result['nModified']} contents modified.")


if __name__ == "__main__":
    db = DB
    app.run(host=HOST, port=PORT, debug=DEBUG)
