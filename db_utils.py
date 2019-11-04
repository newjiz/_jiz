from config import LOGGER as log
from config import DB as db
from bson.objectid import ObjectId

from utils import error

def db_get_user(data):
	"""
	Gets a user from the db by it's username

	Parameters
	----------
		data: object
			Has key "user_id" with str

	Returns
	-------
		Object
			If the user is found

		404
			If user not found
	"""

	try:
		user_id = ObjectId(data["user_id"])
	
	except Exception as e:
		return error(message=str(e))

	user = db.users.find_one({"_id": user_id})

	if user is None:
		return error("User not found", 404)

	return user
