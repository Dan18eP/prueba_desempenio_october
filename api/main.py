import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from api.core.config import settings
from api.core.database import engine_admin
from api.core.security import get_password_hash

# Routers
from api.routers.auth import router as auth_router
from api.routers.kpis import router as kpis_router
from api.routers.events import router as events_router
from api.routers.stream import router as stream_router
from api.routers.reports import router as reports_router
from api.routers.admin import router as admin_router
from api.routers.chat import router as chat_router
from api.routers.governance import router as governance_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("sismowatch.api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown routines."""
    logger.info("Initializing SismoWatch API Backend...")
    # Ensure seed users exist in database on startup
    try:
        with engine_admin.connect() as conn:
            admin_hash = get_password_hash("AdminSismo2026!")
            viewer_hash = get_password_hash("ViewerSismo2026!")
            
            conn.execute(text("""
                INSERT INTO audit.users (username, email, hashed_password, role)
                VALUES 
                    ('admin', 'admin@sismowatch.gov.co', :a_hash, 'admin'),
                    ('viewer', 'viewer@sismowatch.gov.co', :v_hash, 'viewer')
                ON CONFLICT (username) DO NOTHING;
            """), {"a_hash": admin_hash, "v_hash": viewer_hash})
            conn.commit()
            logger.info("Default seed users verified in audit.users table.")
    except Exception as e:
        logger.warning(f"Could not seed users on startup (DB may not be ready yet): {e}")

    yield
    logger.info("Shutting down SismoWatch API Backend...")

app = FastAPI(
    title="SismoWatch API - Operational Seismic Intelligence",
    description="""
    API RESTful de alto rendimiento para SismoWatch SuperApp.
    
    ### Características Clave:
    - **Seguridad RBAC:** Roles `viewer` y `admin` con autenticación JWT (HS256).
    - **Tiempo Real:** Server-Sent Events (SSE) en `/api/stream` con reconexión automática.
    - **Gobernanza:** Trazabilidad OpenMetadata pura (20 in -> 20 out) y auditoría de cuarentena no destructiva.
    - **Agente IA Dual:** Motor Text-to-SQL local (`qwen2.5-coder:3b`) y Gemini con protocolo de gráficos declarativos Chart.js.
    """,
    version="2.4.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(auth_router)
app.include_router(kpis_router)
app.include_router(events_router)
app.include_router(stream_router)
app.include_router(reports_router)
app.include_router(admin_router)
app.include_router(chat_router)
app.include_router(governance_router)

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "HEALTHY",
        "service": "SismoWatch API",
        "version": "2.4.0",
        "environment": settings.ENVIRONMENT,
        "llm_provider": settings.LLM_PROVIDER,
        "ollama_model": settings.OLLAMA_MODEL
    }

@app.get("/", tags=["Root"])
def root():
    return {
        "service": "SismoWatch API",
        "version": "2.4.0",
        "documentation": "/docs",
        "status": "OPERATIONAL"
    }
