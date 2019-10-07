import os
import logging

from random import choices
from datetime import datetime
from dotenv import load_dotenv
from flask_cors import CORS

from flask import Flask, request
import pymysql

from pymongo import MongoClient
from bson.json_util import dumps
from bson.objectid import ObjectId

load_dotenv()
db, _db = None, None
log = logging.getLogger(__name__)

app = Flask(__name__)
cors = CORS(app)

def serialize_user(user_data):
    """
    User model schema:
    ['id', 'username', 'password', 'email']
    """
    
    return {"id": user_data[0], "username": user_data[1], "email": user_data[3]}

def serialize_content(content):
    """
    Content model schema:
    ['id', 'user_id', 'content', 'up', 'down', 'created']
    """
    
    return {
            "id": content[0], 
            "user_id": content[1], 
            "content": content[2],
            "up": content[3],
            "down": content[4],
            "created": datetime.timestamp(content[5]),
            "score": content[3] - content[4]
            }

def ok(message="Ok", code=200):
    return {"message": message}, code

def error(message="Bad request", code=400):
    return {"message": message}, code

@app.route("/", methods=["GET"])
def index():
    log.info(_db.list_collection_names())
    users = [u for u in _db.users.find()]    
    return dumps({"data": users}), 200

@app.route("/u/<id>", methods=["GET"])
def get_user(id):
    try:
        user_id = int(id)
    except Exception as e:
        return error("Id should be and integer", 400)

    with db.cursor() as cursor:
        cursor.execute("select * from user where id = {id}".format(id=user_id))
        data = cursor.fetchone() 
    db.commit()

    if data is None:
        return error("User not found", 404)

    return {"data": serialize_user(data)}


@app.route("/u/<id>/c", methods=["get"])
def get_user_content(id):
    try:
        user_id = int(id)
    except Exception as e:
        return error("id should be and integer", 400)

    with db.cursor() as cursor:
        cursor.execute("select * from content where user_id = {id}".format(id=user_id))
        data = cursor.fetchall() 
    db.commit()

    if data is None:
        return error("content not found", 404)

    return {"data": [serialize_content(c) for c in data]}

@app.route("/u/<id>/c/<c_id>", methods=["get"])
def get_user_content_by_id(id, c_id):
    try:
        user_id = int(id)
    except Exception as e:
        return error("id should be and integer", 400)

    try:
        content_id = int(c_id)
    except Exception as e:
        return error("content id should be and integer", 400)
    
    with db.cursor() as cursor:
        cursor.execute(
                f"select * from content where user_id = {user_id} and id = {c_id}"
                )
        data = cursor.fetchall() 
    db.commit()

    if data is None:
        return error("content not found", 404)

    return {"data": [serialize_content(c) for c in data]}


@app.route("/u/<id>/s", methods=["get"])
def get_user_stack(id):
    try:
        user_id = int(id)
    except Exception as e:
        return error("id should be and integer", 400)

    choice_len = 2

    with db.cursor() as cursor:
        cursor.execute(
                f"select * from content "
                f"where user_id != {user_id} "
                f"order by rand() limit {choice_len}"
                )
        data = cursor.fetchall()
    db.commit()

    if data is None:
        return {"data": []}, 200

    if len(data) < 2:
        return {"data": []}, 200

    stack = choices(data, k=2)
    return {"data": [serialize_content(s) for s in stack]}


@app.route("/u/<id>/v/<c_id>/<vote>", methods=["post"])
def vote_content(id, c_id, vote):
    try:
        user_id = int(id)
    except Exception as e:
        return error("id should be and integer", 400)

    try:
        content_id = int(c_id)
    except Exception as e:
        return error("content id should be and integer", 400)
    
    """
    0: -1 (++down)
    1: +1 (++up)
    2: no action
    """
    valid_votes = [0, 1, 2]

    try:
        vote = int(vote)
        
        if vote not in valid_votes:
            raise Exception("Not valid vote")
    except Exception as e:
        return error(f"vote should be and integer {valid_votes}: {e}", 400)
    
    if vote > 1:
        return {"message": "OK: Skip"}, 200
    
    key = "up" if vote == 1 else "down"

    with db.cursor() as cursor:
        try:
            cursor.execute(f"select count(id) from content where user_id = {user_id} and id = {c_id}")
        except Exception as e:
            log.error(e)
            return error(f"Raised exception: {e}", 400)

        data = cursor.fetchone()

    if data[0] > 0:
        return error("You cannot vote urself, bastard", 400)

    with db.cursor() as cursor:
        cursor.execute(
                f"update content set {key} = {key} + 1 "
                f"where id = {c_id}"
                )
    db.commit()
    
    return {"message": "OK"}, 200

@app.route("/content/<id>", methods=["get"])
def content_get(id):
    
    try:
        _id = ObjectId(str(id)) 
        user = _db.users.find_one({"_id": _id})

        if user is None:
            return error(f"User '{id}' not found", 404)

    except Exception as e:
        log.error(e)
        return error(f"The given id ({id}) is not valid", 400)

    try:
        content = _db.content.find_one({"user_id": _id})

        if content is None:
            return {"data": None}, 200

    except Exception as e:
        log.info(e)
        return error(f"Raised exception: {e}", 400)

    return dumps({"data": content}), 200

@app.route("/content", methods=["post"])
def content_post():
    data = request.json
    
    if "user_id" not in data.keys():
        return error("No 'user_id' key", 400)

    try:
        user = _db.users.find_one({"_id": ObjectId(data["user_id"])})

        if user is None:
            return error(f"User {data['user_id']} not found'", 404)

    except Exception as e:
        log.error(e)
        return error(f"Raised exception: {e}", 400)

    try:
        _c = _db.content.find_one({"user_id": user["_id"]}) 

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

        content_id = _db.content.insert_one(content).inserted_id

    except Exception as e:
        log.error(e)
        return error(f"Raised exception: {e}", 400)

    return {"message": f"Content uploaded: {content_id}"}, 200


@app.route("/u/<id>/c", methods=["post"])
def post_user_content(id):
    try:
        user_id = int(id)
    except Exception as e:
        return error("id should be and integer", 400)
    
    data = request.json
    
    if "content" not in data.keys():
        return error("request json should contain 'content' key and val.")

    try:
        content = str(data["content"])
    
    except Exception as e:
        return error(f"Could not parse content: {e}", 400)

    with db.cursor() as cursor:
        cursor.execute(f"select count(id) from content where user_id = {user_id}")
        count = cursor.fetchone()
    db.commit()

    if count[0] > 0:
        return error(f"User {user_id} already in the contest", 403)

    with db.cursor() as cursor:
        cursor.execute(f"call content_insert({user_id},'{content}')")
    db.commit()

    return {"message": "Content uploaded"}, 200

@app.route("/r", methods=["get"])
def ranking():
    query = """
    select 
        c.id, c.user_id, u.username, c.content, c.up - c.down as s
    from
        jiz.content as c, jiz.user as u 
    where 
        c.user_id = u.id 
    order by 
        s
    desc;
    """

    with db.cursor() as cursor:
        cursor.execute(query)
        raw_data = cursor.fetchall()
    db.commit()

    data = {"data": []}
    pos = 1

    for r in raw_data:
        data["data"].append({
                "position": pos,
                "id": r[0],
                "user_id": r[1],
                "username": r[2],
                "content": r[3],
                "score": r[4]
            })

        pos += 1

    return data, 200

if __name__ == "__main__":
    db = pymysql.connect(
            host=os.environ["HOST"],
            user=os.environ["USER"],
            passwd=os.environ["PASS"],
            db=os.environ["DB"]
            ) 

    mongo = MongoClient(
        os.environ["MONGO_HOST"],
        int(os.environ["MONGO_PORT"])
        )
    _db = mongo.jiz

    app.run(host="0.0.0.0", port=5000, debug=True)
