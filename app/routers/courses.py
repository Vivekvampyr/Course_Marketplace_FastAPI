from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import os, shutil
from app.database import get_db
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.schemas.course import CourseCreate, CourseUpdate, CourseResponse, CourseListResponse
from app.dependencies.auth import get_current_user, require_instructor
from app.models.user import User
from app.config import settings

router = APIRouter(prefix="/courses", tags=["Courses"])

# ── List all published courses ─────────────────────────
@router.get("/", response_model=List[CourseListResponse])
def get_courses(
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    query = db.query(Course).filter(Course.is_published == True)
    if category:
        query = query.filter(Course.category == category)
    return query.offset(skip).limit(limit).all()

# ── Get single course ──────────────────────────────────
@router.get("/{course_id}", response_model=CourseResponse)
def get_course(course_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

# ── Instructor: my courses ─────────────────────────────
@router.get("/my/courses", response_model=List[CourseResponse])
def my_courses(
    current_user: User = Depends(require_instructor),
    db: Session = Depends(get_db)
):
    return db.query(Course).filter(Course.instructor_id == current_user.id).all()

# ── Create course ──────────────────────────────────────
@router.post("/", response_model=CourseResponse)
async def create_course(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    price: float = Form(...),
    category: Optional[str] = Form(None),
    level: str = Form("beginner"),
    thumbnail: Optional[UploadFile] = File(None),
    current_user: User = Depends(require_instructor),
    db: Session = Depends(get_db)
):
    course = Course(
        title=title,
        description=description,
        price=price,
        category=category,
        level=level,
        instructor_id=current_user.id
    )
    db.add(course)
    db.commit()
    db.refresh(course)

    # Save thumbnail if provided
    if thumbnail:
        folder = os.path.join(settings.UPLOAD_DIR, "thumbnails")
        os.makedirs(folder, exist_ok=True)
        file_path = os.path.join(folder, f"{course.id}_{thumbnail.filename}")
        with open(file_path, "wb") as f:
            shutil.copyfileobj(thumbnail.file, f)
        course.thumbnail = file_path
        db.commit()
        db.refresh(course)

    return course

# ── Update course ──────────────────────────────────────
@router.put("/{course_id}", response_model=CourseResponse)
def update_course(
    course_id: int,
    data: CourseUpdate,
    current_user: User = Depends(require_instructor),
    db: Session = Depends(get_db)
):
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.instructor_id == current_user.id
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(course, field, value)

    db.commit()
    db.refresh(course)
    return course

# ── Delete course ──────────────────────────────────────
@router.delete("/{course_id}")
def delete_course(
    course_id: int,
    current_user: User = Depends(require_instructor),
    db: Session = Depends(get_db)
):
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.instructor_id == current_user.id
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    db.delete(course)
    db.commit()
    return {"message": "Course deleted successfully"}

# ── Check enrollment ───────────────────────────────────
@router.get("/{course_id}/enrolled")
def check_enrollment(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.course_id == course_id
    ).first()
    return {"enrolled": enrollment is not None}