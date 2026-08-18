"""
Authentication and authorization dependencies for the BBAC Simulator.
Uses bcrypt directly (not via passlib) for Python 3.14 compatibility —
passlib[bcrypt] has a known incompatibility with bcrypt 4.x.
"""

import bcrypt as _bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from config import settings

# OAuth2 scheme — extracts Bearer token from the Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ---------------------------------------------------------------------------
# Password hashing — using bcrypt directly, no passlib dependency
# ---------------------------------------------------------------------------

def _hash_password(password: str) -> str:
    """Hashes a plain-text password using bcrypt."""
    return _bcrypt.hashpw(
        password.encode("utf-8"),
        _bcrypt.gensalt(),
    ).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain-text password against its bcrypt hash."""
    return _bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# ---------------------------------------------------------------------------
# Hardcoded user store — loaded from .env via settings.
# Passwords are hashed once at startup; plain text is never stored anywhere.
# ---------------------------------------------------------------------------
USERS_DB: Dict[str, Dict[str, str]] = {
    settings.ADMIN_USERNAME: {
        "username": settings.ADMIN_USERNAME,
        "hashed_password": _hash_password(settings.ADMIN_PASSWORD),
        "role": "admin",
    },
    settings.USER_USERNAME: {
        "username": settings.USER_USERNAME,
        "hashed_password": _hash_password(settings.USER_PASSWORD),
        "role": "user",
    },
}


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def authenticate_user(username: str, password: str) -> Optional[Dict[str, str]]:
    """
    Validates credentials against the hardcoded user store.
    Returns {username, role} on success, None on failure.
    """
    user = USERS_DB.get(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return {"username": user["username"], "role": user["role"]}


def create_access_token(data: Dict) -> str:
    """Creates a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

async def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> Dict[str, str]:
    """
    Validates the Bearer JWT and returns {username, role}.
    Raises HTTP 401 if missing, invalid, or expired.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials — please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        username: Optional[str] = payload.get("sub")
        role: Optional[str] = payload.get("role")
        if username is None or role is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    if username not in USERS_DB:
        raise credentials_exception

    return {"username": username, "role": role}


async def require_admin(
    current_user: Dict[str, str] = Depends(get_current_user),
) -> Dict[str, str]:
    """Raises HTTP 403 if the authenticated user is not an admin."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required to access this resource.",
        )
    return current_user


async def require_user(
    current_user: Dict[str, str] = Depends(get_current_user),
) -> Dict[str, str]:
    """Allows any authenticated user (admin or regular user)."""
    return current_user