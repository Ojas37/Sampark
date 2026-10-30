from datetime import timedelta
from typing import Annotated

import jwt
from argon2 import PasswordHasher
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from sqlalchemy.orm import Session

from .clock import Clock
from .config import settings
from .db import get_db
from .models import User


password_hasher = PasswordHasher()
bearer = HTTPBearer(auto_error=False)
DbSession = Annotated[Session, Depends(get_db)]


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def create_access_token(user: User) -> str:
    now = Clock.now()
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "region_code": user.region_code,
        "institution_id": user.institution_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: DbSession,
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "AUTH_REQUIRED", "message": "Sign in to continue", "details": {}})
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "INVALID_TOKEN", "message": "Your session is invalid or expired", "details": {}})
    user = db.get(User, user_id)
    if user is None or not user.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "INVALID_USER", "message": "User is unavailable", "details": {}})
    return user


def require(*roles: str):
    def dependency(user: Annotated[User, Depends(current_user)]) -> User:
        if roles and user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "FORBIDDEN_ROLE", "message": "Your role cannot perform this action", "details": {"required_roles": roles}})
        return user
    return dependency


def ensure_case_scope(user: User, application: object) -> None:
    if user.role == "INSTITUTION_APPLICANT" and user.institution_id != getattr(application, "institution_id"):
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Application not found", "details": {}})
    if user.region_code and user.role in {"SCRUTINY_OFFICER", "EVC_COORDINATOR", "REGIONAL_OFFICER"}:
        if user.region_code != getattr(application, "region_code"):
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Application not found", "details": {}})
