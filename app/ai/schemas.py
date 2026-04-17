from pydantic import BaseModel
from typing import Optional, List

class AgentIntent(BaseModel):
    intent: str
    table: Optional[str] = None
    filters: List[str] = []
    metric: Optional[str] = None
    raw_question: str
