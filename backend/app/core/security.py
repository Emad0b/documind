import hashlib, hmac, secrets, time, uuid
from fastapi import Cookie, HTTPException, Request, Response
from .database import db, sql
from .config import SECURE_COOKIES


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    return (
        salt
        + ":"
        + hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 310000).hex()
    )


def issue_session(response: Response, owner: str):
    token = secrets.token_urlsafe(32)
    with db() as conn:
        sql(conn, "DELETE FROM sessions WHERE expires < ?", (time.time(),))
        sql(
            conn,
            "INSERT INTO sessions VALUES (?,?,?)",
            (
                hashlib.sha256(token.encode()).hexdigest(),
                owner,
                time.time() + 7 * 86400,
            ),
        )
    response.set_cookie(
        "documind_session",
        token,
        httponly=True,
        samesite="strict",
        secure=SECURE_COOKIES,
        max_age=7 * 86400,
    )


def current_user(request: Request, documind_session: str | None = Cookie(default=None)):
    origin = request.headers.get("origin")
    if request.method not in ("GET", "HEAD", "OPTIONS") and origin:
        from urllib.parse import urlparse

        if urlparse(origin).netloc != request.headers.get("host"):
            raise HTTPException(403, "Cross-origin writes are not allowed")
    if not documind_session:
        raise HTTPException(401, "Sign in or open a guest workspace")
    with db() as conn:
        row = sql(
            conn,
            "SELECT owner FROM sessions WHERE token=? AND expires>?",
            (hashlib.sha256(documind_session.encode()).hexdigest(), time.time()),
        ).fetchone()
    if not row:
        raise HTTPException(401, "Session expired")
    return row[0]


def authorize_documents(owner, ids):
    if not ids:
        raise HTTPException(400, "Select at least one document")
    with db() as conn:
        for did in set(ids):
            row = sql(
                conn,
                "SELECT status FROM documents WHERE id=? AND owner=?",
                (did, owner),
            ).fetchone()
            if not row:
                raise HTTPException(404, "Document not found")
            if row[0] != "ready":
                raise HTTPException(409, "Document is not ready for questions")
