import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta
from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from models import RefreshSession, SessionLocal, User

SECRET_KEY = os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY")
if not SECRET_KEY or SECRET_KEY in {"dev-secret-key", "change-this-secret-key"}:
    raise RuntimeError("JWT_SECRET_KEY or a strong SECRET_KEY is required")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
OPERATIONAL_ROLES = {"SUPER_ADMIN", "ADMIN", "DISPATCHER", "SUPERVISOR", "RESPONDER", "INTELLIGENCE_OFFICER", "MEDICAL_OPERATOR", "AGENCY_ADMIN", "CITIZEN"}


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return "scrypt$" + base64.urlsafe_b64encode(salt + digest).decode()


def verify_password(password: str, encoded: str) -> bool:
    try:
        raw = base64.urlsafe_b64decode(encoded.removeprefix("scrypt$").encode())
        salt, expected = raw[:16], raw[16:]
        actual = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def issue_token(user: User, token_type: str, lifetime: timedelta, session_id: str | None = None) -> str:
    expires = datetime.utcnow() + lifetime
    payload = {"sub": user.id, "type": token_type, "exp": expires}
    if session_id:
        payload["sid"] = session_id
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_refresh_token(db: Session, user: User) -> str:
    session_id = os.urandom(16).hex()
    token = issue_token(user, "refresh", timedelta(days=REFRESH_DAYS), session_id=session_id)
    db.add(RefreshSession(
        id=session_id,
        user_id=user.id,
        token_hash=token_hash(token),
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_DAYS),
    ))
    return token


def rotate_refresh_token(db: Session, token: str) -> tuple[User, str]:
    credentials_error = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh" or not payload.get("sid"):
            raise credentials_error
    except JWTError as exc:
        raise credentials_error from exc
    session = db.query(RefreshSession).filter(
        RefreshSession.id == payload["sid"],
        RefreshSession.token_hash == token_hash(token),
        RefreshSession.revoked_at.is_(None),
    ).first()
    if not session or session.expires_at <= datetime.utcnow() or not session.user.is_active:
        raise credentials_error
    session.revoked_at = datetime.utcnow()
    replacement = create_refresh_token(db, session.user)
    return session.user, replacement


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_error = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise credentials_error
        user = db.query(User).filter(User.id == payload.get("sub"), User.is_active.is_(True)).first()
    except JWTError as exc:
        raise credentials_error from exc
    if user is None:
        raise credentials_error
    return user


def require_roles(*roles: str) -> Callable:
    def dependency(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
    return dependency