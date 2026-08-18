"""
Authentication routes for the BBAC Simulator.
Provides login (JWT issuance), logout, and current-user-info endpoints.

Token lifecycle:
  POST /api/auth/login   → issue JWT (valid for JWT_EXPIRE_MINUTES from .env)
  GET  /api/auth/me      → return username + role for the active token
  POST /api/auth/logout  → client-side signal; server returns confirmation
                           (JWTs are stateless — actual invalidation requires
                           a token blocklist, planned for the DB-auth migration)
"""

from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from api.dependencies import (
    authenticate_user,
    create_access_token,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Dict[str, str]:
    """
    Authenticate a user and return a JWT access token.

    Accepts standard OAuth2 form data (username + password).
    Returns the token, token type, user role, and username so the
    frontend can immediately route the user to the correct interface
    without a separate /me call.
    """
    user = authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"]}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user["role"],
        "username": user["username"],
    }


@router.get("/me")
async def get_me(
    current_user: Dict[str, str] = Depends(get_current_user),
) -> Dict[str, str]:
    """
    Returns the username and role of the currently authenticated user.
    Requires a valid Bearer token in the Authorization header.
    Used by the frontend on page load to restore session state.
    """
    return current_user


@router.post("/logout")
async def logout(
    current_user: Dict[str, str] = Depends(get_current_user),
) -> Dict[str, str]:
    """
    Client-side logout signal.
    The frontend clears its stored token on receipt of this response.

    Note: JWT tokens are stateless — this endpoint does not invalidate
    the token server-side. Full server-side logout (token blocklist) is
    planned for the database-auth migration phase.
    """
    return {
        "message": f"User '{current_user['username']}' logged out successfully.",
        "status": "logged_out",
    }