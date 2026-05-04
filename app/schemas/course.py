from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.course import CourseLevel

class CourseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    price: float = 0.0
    category: Optional[str] = None
    level: CourseLevel = CourseLevel.beginner

class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    level: Optional[CourseLevel] = None
    is_published: Optional[bool] = None

class LectureResponse(BaseModel):
    id: int
    title: str
    duration: Optional[float]
    order_index: int
    is_free_preview: bool

    class Config:
        from_attributes = True

class CourseResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    price: float
    thumbnail: Optional[str]
    category: Optional[str]
    level: CourseLevel
    is_published: bool
    instructor_id: int
    created_at: datetime
    lectures: List[LectureResponse] = []

    class Config:
        from_attributes = True

class CourseListResponse(BaseModel):
    id: int
    title: str
    price: float
    thumbnail: Optional[str]
    category: Optional[str]
    level: CourseLevel
    instructor_id: int

    class Config:
        from_attributes = True