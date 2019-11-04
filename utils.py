import re
import jwt

from config import JWT_SECRET, JWT_ALG

regex = r"(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|\"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*\")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])"

def valid_mail(mail):
	check = re.match(regex, mail)

	if check:
		return True

	return False


def encode(data, secret=JWT_SECRET, algorithm=JWT_ALG):
	token = jwt.encode(data, secret, algorithm=algorithm)
	return token.decode()


def decode(token, secret=JWT_SECRET, algorithms=[JWT_ALG]):
	try:
		data = jwt.decode(token, secret, algorithms=algorithms)
		return data

	except Exception:
		return None

def ok(message="Ok", code=200):
    """Sample HTTP 200 OK response."""
    return {"message": message}, code


def error(message="Bad request", code=400):
    """Sample HTTP 400 error response."""
    return {"message": message}, code
