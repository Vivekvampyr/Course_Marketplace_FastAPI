from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class LectureCreate(BaseModel):
    title: str
    order_index: int = 0
    is_free_preview: bool = False

class LectureUpdate(BaseModel):
    title: Optional[str] = None
    order_index: Optional[int] = None
    is_free_preview: Optional[bool] = None

class LectureResponse(BaseModel):
    id: int
    title: str
    video_path: Optional[str]
    duration: Optional[float]
    order_index: int
    is_free_preview: bool
    course_id: int
    created_at: datetime

    class Config:
        from_attributes = True