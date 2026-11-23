class InvalidRequest(Exception):
    """The request is malformed or missing a required value (400)."""


class NotPermitted(Exception):
    """The actor is not allowed to perform this action (403)."""


class NotFound(Exception):
    """The requested listing does not exist (404)."""
