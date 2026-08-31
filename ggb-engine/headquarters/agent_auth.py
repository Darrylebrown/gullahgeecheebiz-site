"""
Bearer-token authentication middleware for internal GGB agents.

Usage (Flask):
    from agent_auth import require_agent_auth, AGENT_TOKEN
    app = Flask(__name__)
    app.config["AGENT_TOKEN"] = os.environ["AGENT_TOKEN_PUBLISHING_CONTROLLER"]

    @app.before_request
    def _auth(): require_agent_auth()

Usage (FastAPI):
    from agent_auth import fastapi_auth_dependency
    @app.get("/x", dependencies=[Depends(fastapi_auth_dependency("AGENT_TOKEN_BOT_FACTORY"))])

Usage (http.server / raw): wrap handler with wrap_http_handler(handler, expected_token).
"""
import os, hmac, functools
from flask import request, abort

def _safe_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())

def require_agent_auth(env_var=None):
    """Flask before_request hook. Pass env_var to override auto-detection."""
    token = request.headers.get("Authorization", "")
    if token.startswith("Bearer "):
        token = token[7:]
    expected = os.environ.get(env_var) if env_var else None
    if not expected:
        # Fall back to any AGENT_TOKEN_* in env
        for k, v in os.environ.items():
            if k.startswith("AGENT_TOKEN_"):
                expected = v
                break
    if not expected or not _safe_eq(token or "", expected):
        abort(401)

def fastapi_auth_dependency(env_var: str):
    def _dep(request):
        from fastapi import HTTPException
        auth = request.headers.get("Authorization", "")
        token = auth[7:] if auth.startswith("Bearer ") else ""
        expected = os.environ.get(env_var, "")
        if not _safe_eq(token, expected):
            raise HTTPException(status_code=401, detail="Unauthorized")
    return _dep
