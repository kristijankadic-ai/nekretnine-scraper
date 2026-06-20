import functools
import hmac

from flask import Response, request

from config import Config


def requires_agent_auth(view):
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        auth = request.authorization
        valid = (
            auth
            and hmac.compare_digest(auth.username or "", Config.AGENT_USERNAME)
            and hmac.compare_digest(auth.password or "", Config.AGENT_PASSWORD)
        )
        if not valid:
            return Response(
                "Authentication required",
                401,
                {"WWW-Authenticate": 'Basic realm="Agent area"'},
            )
        return view(*args, **kwargs)

    return wrapper
