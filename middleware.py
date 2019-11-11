from functools import wraps
from flask import g, request, redirect, url_for

from utils import error, decode

def auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "AUTHORIZATION" not in request.headers:
            return error(message="No authorization", code=401)

        token = request.headers["AUTHORIZATION"]

        if "Bearer" in request.headers["AUTHORIZATION"]:
            token = token.split()[1] 
        
        request.jwt_data = decode(token)

        return f(*args, **kwargs)

    return decorated_function