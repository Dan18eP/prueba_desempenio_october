from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status, Query, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import bcrypt
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from api.core.config import settings
from api.core.database import get_admin_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

class TokenData(BaseModel):
    username: str
    role: str
    email: Optional[str] = None

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8")[:72], hashed_password.encode("utf-8"))
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """Generates a secure bcrypt hash with 12 rounds of salt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8")[:72], salt).decode("utf-8")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Encodes a signed JWT with expiration and user role claims."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def get_current_user(
    request: Request,
    token_header: Optional[str] = Depends(oauth2_scheme),
    token_query: Optional[str] = Query(None, alias="token"),
    db: Session = Depends(get_admin_db)
) -> TokenData:
    """
    Validates JWT token from either 'Authorization: Bearer <token>' header
    or '?token=<token>' query parameter (essential for browser SSE EventSource).
    Returns TokenData or raises HTTP 401 Unauthorized.
    """
    token = token_header or token_query
    
    # Also check cookie if present
    if not token and "access_token" in request.cookies:
        token = request.cookies.get("access_token")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales de autenticación no válidas o sesión expirada.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub") or payload.get("username")
        role: str = payload.get("role")
        email: str = payload.get("email")
        if username is None or role is None:
            raise credentials_exception
        return TokenData(username=username, role=role, email=email)
    except JWTError:
        raise credentials_exception

def require_admin(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """
    Enforces RBAC: Only users with role 'admin' can proceed.
    Viewers receive strict HTTP 403 Forbidden (PDF Pág. 3 y 7).
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso Denegado: Esta acción requiere permisos de administrador."
        )
    return current_user
