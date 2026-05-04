from pydantic import BaseModel
from datetime import datetime
from app.schemas.course import CourseListResponse

class CartAddRequest(BaseModel):
    course_id: int

class CartItemResponse(BaseModel):
    id: int
    course_id: int
    added_at: datetime
    course: CourseListResponse

    class Config:
        from_attributes = True