import json
import os

from dateutil.parser import parse
from datetime import datetime
from dotenv import load_dotenv

from flask import Flask
import pymysql

load_dotenv()
db = None

app = Flask(__name__)

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
            "created": datetime.timestamp(content[5])
            }

def ok(message="Ok", code=200):
    return {"message": message}, code

def error(message="Bad request", code=400):
    return {"message": message}, code

@app.route("/", methods=["GET"])
def index():
    return ok()

@app.route("/<id>", methods=["GET"])
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


@app.route("/<id>/content", methods=["GET"])
def get_user_content(id):
    try:
        user_id = int(id)
    except Exception as e:
        return error("Id should be and integer", 400)

    with db.cursor() as cursor:
        cursor.execute("select * from content where user_id = {id}".format(id=user_id))
        data = cursor.fetchall() 
    db.commit()

    if data is None:
        return error("Content not found", 404)

    return {"data": [serialize_content(c) for c in data]}


if __name__ == "__main__":
    db = pymysql.connect(
            host=os.environ["HOST"],
            user=os.environ["USER"],
            passwd=os.environ["PASS"],
            db=os.environ["DB"]
            ) 

    app.run(host="0.0.0.0", port=5000, debug=True)
