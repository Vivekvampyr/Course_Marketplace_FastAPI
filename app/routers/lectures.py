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
from fastapi.responses import StreamingResponse
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from app.services.video_service import stream_video
from app.utils.jwt import decode_token

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

# In routers/lectures.py — add this function
async def get_user_from_header_or_query(
    request: Request,
    token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    # Try query param first (web video player)
    raw_token = token
    # Then try Authorization header
    if not raw_token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            raw_token = auth_header.split(" ")[1]

    if not raw_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_token(raw_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == int(payload.get("sub"))).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# ── Stream video ───────────────────────────────────────
@router.get("/{lecture_id}/stream")
async def stream_lecture(
    lecture_id: int,
    request: Request,
    token: Optional[str] = None,
    current_user: User = Depends(get_user_from_header_or_query),
    db: Session = Depends(get_db)
):
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")

    if not lecture.is_free_preview:
        enrollment = db.query(Enrollment).filter(
            Enrollment.user_id == current_user.id,
            Enrollment.course_id == lecture.course_id
        ).first()
        if not enrollment:
            course = db.query(Course).filter(Course.id == lecture.course_id).first()
            if course.instructor_id != current_user.id:
                raise HTTPException(status_code=403, detail="Purchase this course to watch")

    # Fix path separators
    video_path = lecture.video_path.replace("\\", "/") if lecture.video_path else None

    range_header = request.headers.get("Range")
    response = await stream_video(video_path, range_header)

    # ← Add CORS headers for web
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Cross-Origin-Resource-Policy"] = "cross-origin"

    return response

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