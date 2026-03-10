"""
Authentication module for the NeuroArousal Exhibit API.

Provides JWT-based authentication with:
  * User registration and login
  * Password hashing with bcrypt
  * Bearer token authentication dependency
  * Simple JSON file-based user store (suitable for exhibit/kiosk use)
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

import hashlib
import hmac
import base64
import secrets

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SECRET_KEY = os.environ.get("NEUROAROUSAL_SECRET_KEY", secrets.token_hex(32))
TOKEN_EXPIRE_SECONDS = int(os.environ.get("NEUROAROUSAL_TOKEN_EXPIRE", "3600"))
USERS_FILE = Path(os.environ.get("NEUROAROUSAL_USERS_FILE", "users.json"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str = Field("", max_length=100)


class UserOut(BaseModel):
    username: str
    display_name: str
    created_at: float


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ---------------------------------------------------------------------------
# Password hashing (PBKDF2-SHA256, no extra deps needed)
# ---------------------------------------------------------------------------

def _hash_password(password: str, salt: bytes | None = None) -> str:
    """Hash password with PBKDF2-SHA256. Returns 'salt$hash' string."""
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return base64.b64encode(salt).decode() + "$" + base64.b64encode(dk).decode()


def _verify_password(password: str, stored: str) -> bool:
    """Verify password against stored 'salt$hash' string."""
    salt_b64, hash_b64 = stored.split("$", 1)
    salt = base64.b64decode(salt_b64)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    expected = base64.b64decode(hash_b64)
    return hmac.compare_digest(dk, expected)


# ---------------------------------------------------------------------------
# Token creation / verification (simple HMAC-based, no JWT library needed)
# ---------------------------------------------------------------------------

def _create_token(username: str) -> tuple[str, int]:
    """Create a signed token. Returns (token_string, expires_in_seconds)."""
    expires_at = int(time.time()) + TOKEN_EXPIRE_SECONDS
    payload = f"{username}:{expires_at}"
    sig = hmac.new(
        SECRET_KEY.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    token = base64.urlsafe_b64encode(f"{payload}:{sig}".encode()).decode()
    return token, TOKEN_EXPIRE_SECONDS


def _decode_token(token: str) -> str:
    """Decode and verify token. Returns username or raises HTTPException."""
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        parts = decoded.rsplit(":", 1)
        if len(parts) != 2:
            raise ValueError("bad format")
        payload, sig = parts
        expected_sig = hmac.new(
            SECRET_KEY.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            raise ValueError("bad signature")
        username, expires_at_str = payload.split(":", 1)
        if int(expires_at_str) < int(time.time()):
            raise ValueError("expired")
        return username
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# User store (JSON file)
# ---------------------------------------------------------------------------

def _load_users() -> dict:
    if USERS_FILE.exists():
        return json.loads(USERS_FILE.read_text())
    return {}


def _save_users(users: dict) -> None:
    USERS_FILE.write_text(json.dumps(users, indent=2))


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------

def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    """FastAPI dependency that returns the authenticated username."""
    username = _decode_token(token)
    users = _load_users()
    if username not in users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return username


def optional_user(token: str | None = Depends(oauth2_scheme)) -> str | None:
    """FastAPI dependency that returns username if authenticated, else None."""
    if token is None:
        return None
    try:
        return _decode_token(token)
    except HTTPException:
        return None


# ---------------------------------------------------------------------------
# Public functions for router
# ---------------------------------------------------------------------------

def register_user(data: UserCreate) -> UserOut:
    users = _load_users()
    if data.username in users:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )
    now = time.time()
    users[data.username] = {
        "password_hash": _hash_password(data.password),
        "display_name": data.display_name or data.username,
        "created_at": now,
    }
    _save_users(users)
    return UserOut(
        username=data.username,
        display_name=users[data.username]["display_name"],
        created_at=now,
    )


def authenticate_user(username: str, password: str) -> TokenOut:
    users = _load_users()
    user = users.get(username)
    if user is None or not _verify_password(password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token, expires_in = _create_token(username)
    return TokenOut(access_token=token, expires_in=expires_in)
