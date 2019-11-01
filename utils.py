"""Util functions"""


def ok(message="Ok", code=200):
    """Sample HTTP 200 OK response."""
    return {"message": message}, code


def error(message="Bad request", code=400):
    """Sample HTTP 400 error response."""
    return {"message": message}, code
