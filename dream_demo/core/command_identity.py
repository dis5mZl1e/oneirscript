"""Opaque runtime identities for objects referenced by detached UI drafts."""
from uuid import uuid4


def command_object_token(value):
    token = getattr(value, '_command_object_token', None)
    if type(token) is not int or token <= 0:
        token = uuid4().int
        value._command_object_token = token
    return token
