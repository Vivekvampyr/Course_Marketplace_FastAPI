from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.user import UserResponse
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.enrollment import Enrollment
from app.schemas.course import CourseListResponse
from app.config import settings
from typing import List
import os, shutil

router = APIRouter(prefix="/users", tags=["Users"])

# ── Get own profile ────────────────────────────────────
@router.get("/me", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user

# ── Upload avatar ──────────────────────────────────────
@router.post("/me/avatar")
def upload_avatar(
    avatar: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    folder = os.path.join(settings.UPLOAD_DIR, "avatars")
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, f"{current_user.id}_{avatar.filename}")

    with open(file_path, "wb") as f:
        shutil.copyfileobj(avatar.file, f)

    current_user.avatar = file_path
    db.commit()
    return {"message": "Avatar updated", "avatar": file_path}

# ── Get enrolled courses ───────────────────────────────
@router.get("/me/enrollments", response_model=List[CourseListResponse])
def my_enrollments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    enrollments = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id
    ).all()
    return [
        {
            "course_id": e.course_id,
            "enrolled_at": e.enrolled_at,
            "course": e.course
        }
        for e in enrollments
    ]