from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ChatRequest(BaseModel):
    message: str
    course_id: Optional[int] = None   # Pass for course-specific questions

class ChatResponse(BaseModel):
    message: str
    response: str
    created_at: datetime

    class Config:
        from_attributes = True

class ChatHistoryResponse(BaseModel):
    id: int
    message: str
    response: Optional[str]
    course_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True