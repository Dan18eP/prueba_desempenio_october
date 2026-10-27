from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(
    title="SismoWatch API",
    description="Operational Seismic Intelligence API with JWT RBAC, Real-Time SSE and Text-to-SQL AI Agent",
    version="2.4.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "HEALTHY",
        "service": "SismoWatch API",
        "version": "2.4.0",
        "llm_provider": os.getenv("LLM_PROVIDER", "ollama")
    }

@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Welcome to SismoWatch API. Visit /docs for OpenAPI documentation.",
        "status": "OPERATIONAL"
    }
