from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from api.core.database import get_readonly_db
from api.core.security import get_current_user, TokenData
from api.services.llm_client import query_dual_engine

router = APIRouter(prefix="/api/chat", tags=["Text-to-SQL AI Assistant"])

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    prompt: str
    history: Optional[List[ChatMessage]] = None

class ChatResponse(BaseModel):
    answer: str
    chart: dict
    sql_executed: Optional[str] = None
    suggested_questions: Optional[List[str]] = None
    model_used: str
    latency_ms: int
    fallback_active: bool

@router.post("", response_model=ChatResponse)
def ask_ai_assistant(
    request: ChatRequest,
    current_user: Optional[TokenData] = Depends(get_current_user),
    db: Session = Depends(get_readonly_db)
):
    """
    Text-to-SQL AI Assistant endpoint with Dual Engine (Qwen 2.5 / Gemini)
    and Declarative Chart Protocol (Chart.js JSON).
    Protected by OWASP LLM01 prompt injection sanitization and read-only DB permissions.
    """
    if not request.prompt or not request.prompt.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La pregunta no puede estar vacía."
        )

    result = query_dual_engine(user_prompt=request.prompt, db=db)
    return result
