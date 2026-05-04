from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ReviewCreate(BaseModel):
    course_id: int
    rating: int = Field(..., ge=1, le=5)  # 1 to 5 only
    comment: Optional[str] = None

class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None

class ReviewResponse(BaseModel):
    id: int
    user_id: int
    course_id: int
    rating: int
    comment: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True