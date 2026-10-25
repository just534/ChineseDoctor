import re
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import get_settings

ALGORITHM = "HS256"
settings = get_settings()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode())
    except ValueError:
        return False


# Precomputed so that logins for unknown users take as long as for known ones
DUMMY_HASH = hash_password(uuid.uuid4().hex)


def validate_password_strength(password: str) -> str | None:
    if len(password) < 8:
        return "密码至少 8 位"
    if len(password.encode("utf-8")) > 72:
        return "密码过长"
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "密码需同时包含字母和数字"
    return None


def _encode(sub: int, ver: int, typ: str, delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(sub),
        "ver": ver,
        "typ": typ,
        "iat": now,
        "exp": now + delta,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_access_token(user_id: int, token_version: int) -> str:
    return _encode(user_id, token_version, "access", timedelta(minutes=settings.access_token_minutes))


def create_refresh_token(user_id: int, token_version: int) -> str:
    return _encode(user_id, token_version, "refresh", timedelta(days=settings.refresh_token_days))


def decode_token(token: str, expected_type: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("typ") != expected_type:
        return None
    return payload
