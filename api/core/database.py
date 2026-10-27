from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from api.core.config import settings

# Engine para lectura de la plataforma (Mínimo Privilegio - solo SELECT en curated)
engine_readonly = create_engine(
    settings.READONLY_DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_recycle=300,
    pool_pre_ping=True
)

# Engine administrativo para autenticación de usuarios en schema audit
engine_admin = create_engine(
    settings.ADMIN_DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_recycle=300,
    pool_pre_ping=True
)

SessionReadonly = sessionmaker(autocommit=False, autoflush=False, bind=engine_readonly)
SessionAdmin = sessionmaker(autocommit=False, autoflush=False, bind=engine_admin)

Base = declarative_base()

def get_readonly_db():
    db = SessionReadonly()
    try:
        yield db
    finally:
        db.close()

def get_admin_db():
    db = SessionAdmin()
    try:
        yield db
    finally:
        db.close()
