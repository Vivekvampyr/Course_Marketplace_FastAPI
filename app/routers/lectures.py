from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.lecture import Lecture
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.schemas.lecture import LectureCreate, LectureUpdate, LectureResponse
from app.dependencies.auth import get_current_user, require_instructor
from app.services.video_service import save_video, delete_video, stream_video
from app.models.user import User
from typing import List, Optional

router = APIRouter(prefix="/lectures", tags=["Lectures"])

# ── Add lecture + upload video ─────────────────────────
@router.post("/", response_model=LectureResponse)
async def create_lecture(
    course_id: int = Form(...),
    title: str = Form(...),
    order_index: int = Form(0),
    is_free_preview: bool = Form(False),
    video: UploadFile = File(...),
    current_user: User = Depends(require_instructor),
    db: Session = Depends(get_db)
):
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.instructor_id == current_user.id
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Create lecture record first to get ID
    lecture = Lecture(
        title=title,
        order_index=order_index,
        is_free_preview=is_free_preview,
        course_id=course_id
    )
    db.add(lecture)
    db.commit()
    db.refresh(lecture)

    # Save video file
    video_path = await save_video(video, course_id, lecture.id)
    lecture.video_path = video_path
    db.commit()
    db.refresh(lecture)

    return lecture

# ── Stream video ───────────────────────────────────────
@router.get("/{lecture_id}/stream")
async def stream_lecture(
    lecture_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")

    # Allow free preview without enrollment check
    if not lecture.is_free_preview:
        enrollment = db.query(Enrollment).filter(
            Enrollment.user_id == current_user.id,
            Enrollment.course_id == lecture.course_id
        ).first()
        if not enrollment:
            # Also allow instructor to watch their own
            course = db.query(Course).filter(Course.id == lecture.course_id).first()
            if course.instructor_id != current_user.id:
                raise HTTPException(status_code=403, detail="Purchase this course to watch")

    range_header = request.headers.get("Range")
    return await stream_video(lecture.video_path, range_header)

# ── Update lecture ─────────────────────────────────────
@router.put("/{lecture_id}", response_model=LectureResponse)
def update_lecture(
    lecture_id: int,
    data: LectureUpdate,
    current_user: User = Depends(require_instructor),
    db: Session = Depends(get_db)
):
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")

    course = db.query(Course).filter(
        Course.id == lecture.course_id,
        Course.instructor_id == current_user.id
    ).first()
    if not course:
        raise HTTPException(status_code=403, detail="Not authorized")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(lecture, field, value)

    db.commit()
    db.refresh(lecture)
    return lecture

# ── Delete lecture ─────────────────────────────────────
@router.delete("/{lecture_id}")
def delete_lecture(
    lecture_id: int,
    current_user: User = Depends(require_instructor),
    db: Session = Depends(get_db)
):
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")

    course = db.query(Course).filter(
        Course.id == lecture.course_id,
        Course.instructor_id == current_user.id
    ).first()
    if not course:
        raise HTTPException(status_code=403, detail="Not authorized")

    delete_video(lecture.video_path)
    db.delete(lecture)
    db.commit()
    return {"message": "Lecture deleted successfully"}