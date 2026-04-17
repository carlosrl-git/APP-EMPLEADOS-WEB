from fastapi import APIRouter, Request
from pydantic import BaseModel
from app.ai.agent_service import run_agent

router = APIRouter(prefix="/ai", tags=["AI"])

class AgentQuestion(BaseModel):
    question: str

@router.post("/ask")
def ask_agent(request: Request, payload: AgentQuestion):
    session_role = request.session.get("session_role")
    session_user = request.session.get("session_user")
    return {"response": run_agent(payload.question, session_role=session_role, session_user=session_user)}
