from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Lecture(Base):
    __tablename__ = "lectures"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    video_path = Column(String, nullable=True)       # Local file path
    duration = Column(Float, nullable=True)          # In seconds
    order_index = Column(Integer, default=0)         # Order in course
    is_free_preview = Column(Boolean, default=False) # Watchable without purchase
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    course = relationship("Course", back_populates="lectures")