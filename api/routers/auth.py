from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from api.core.config import settings
from api.core.database import get_admin_db, get_readonly_db
from api.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    TokenData
)

router = APIRouter(prefix="/auth", tags=["Authentication & RBAC"])

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

# Fallback in-memory hashes for initial startup before DB seed
SEED_CREDENTIALS = {
    "admin": {
        "password_hash": "$2b$12$0B6a5xZpA9h1E3C7sK9y7.i0UoF8rY2oZ9rV9G5aP1qQ1oE8pZ1eS", # AdminSismo2026!
        "role": "admin",
        "email": "admin@sismowatch.gov.co"
    },
    "viewer": {
        "password_hash": "$2b$12$6K8m1rL9pQ3vX0aB8sD2..u4XyT7uW3oK5vP2bC4mR9sT0vW1yZ3.", # ViewerSismo2026!
        "role": "viewer",
        "email": "viewer@sismowatch.gov.co"
    }
}

@router.post("/login", response_model=LoginResponse)
def login(login_data: LoginRequest, db: Session = Depends(get_admin_db)):
    """
    Authenticates user and returns JWT token.
    Supports 'admin' (full write/quarantine access) and 'viewer' (read-only).
    Checks audit.users database table.
    """
    user_row = None
    try:
        query = text("SELECT id, username, email, hashed_password, role, is_active FROM audit.users WHERE username = :u LIMIT 1")
        result = db.execute(query, {"u": login_data.username}).mappings().first()
        if result:
            user_row = dict(result)
    except Exception as e:
        # DB may still be bootstrapping, fallback checked below
        pass

    authenticated = False
    role = "viewer"
    email = f"{login_data.username}@sismowatch.gov.co"

    if user_row:
        if not user_row.get("is_active", True):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuario inactivo.")
        if verify_password(login_data.password, user_row["hashed_password"]):
            authenticated = True
            role = user_row["role"]
            email = user_row["email"]
    
    # Fallback verification for demo / initialization
    if not authenticated:
        if login_data.username == "admin" and login_data.password == "AdminSismo2026!":
            authenticated = True
            role = "admin"
            email = "admin@sismowatch.gov.co"
            # Ensure user exists in DB
            try:
                hashed = get_password_hash(login_data.password)
                db.execute(text("""
                    INSERT INTO audit.users (username, email, hashed_password, role)
                    VALUES (:u, :e, :h, :r)
                    ON CONFLICT (username) DO UPDATE SET hashed_password = EXCLUDED.hashed_password
                """), {"u": "admin", "e": email, "h": hashed, "r": "admin"})
                db.commit()
            except Exception:
                db.rollback()
        elif login_data.username == "viewer" and login_data.password == "ViewerSismo2026!":
            authenticated = True
            role = "viewer"
            email = "viewer@sismowatch.gov.co"
            try:
                hashed = get_password_hash(login_data.password)
                db.execute(text("""
                    INSERT INTO audit.users (username, email, hashed_password, role)
                    VALUES (:u, :e, :h, :r)
                    ON CONFLICT (username) DO UPDATE SET hashed_password = EXCLUDED.hashed_password
                """), {"u": "viewer", "e": email, "h": hashed, "r": "viewer"})
                db.commit()
            except Exception:
                db.rollback()

    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas. Verifique usuario y contraseña.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    access_token = create_access_token(
        data={"sub": login_data.username, "role": role, "email": email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "username": login_data.username,
            "role": role,
            "email": email
        }
    }

@router.get("/me")
def get_me(current_user: TokenData = Depends(get_current_user)):
    """Returns the authenticated user's profile and active role."""
    return {
        "username": current_user.username,
        "role": current_user.role,
        "email": current_user.email
    }
