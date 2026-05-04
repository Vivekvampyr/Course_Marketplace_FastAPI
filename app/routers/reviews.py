from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from app.database import get_db
from app.models.review import Review
from app.models.enrollment import Enrollment
from app.schemas.review import ReviewCreate, ReviewUpdate, ReviewResponse
from app.dependencies.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/reviews", tags=["Reviews"])

# ── Create review (must be enrolled) ──────────────────
@router.post("/", response_model=ReviewResponse)
def create_review(
    data: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Must be enrolled to review
    enrolled = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.course_id == data.course_id
    ).first()
    if not enrolled:
        raise HTTPException(status_code=403, detail="Purchase this course to leave a review")

    # One review per user per course
    existing = db.query(Review).filter(
        Review.user_id == current_user.id,
        Review.course_id == data.course_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You already reviewed this course")

    review = Review(
        user_id=current_user.id,
        course_id=data.course_id,
        rating=data.rating,
        comment=data.comment
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review

# ── Get all reviews for a course ───────────────────────
@router.get("/course/{course_id}", response_model=List[ReviewResponse])
def get_course_reviews(
    course_id: int,
    db: Session = Depends(get_db)
):
    return db.query(Review).filter(Review.course_id == course_id).all()

# ── Get average rating for a course ───────────────────
@router.get("/course/{course_id}/rating")
def get_course_rating(
    course_id: int,
    db: Session = Depends(get_db)
):
    result = db.query(
        func.avg(Review.rating).label("average"),
        func.count(Review.id).label("total")
    ).filter(Review.course_id == course_id).first()

    return {
        "course_id": course_id,
        "average_rating": round(float(result.average or 0), 1),
        "total_reviews": result.total
    }

# ── Update own review ──────────────────────────────────
@router.put("/{review_id}", response_model=ReviewResponse)
def update_review(
    review_id: int,
    data: ReviewUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    review = db.query(Review).filter(
        Review.id == review_id,
        Review.user_id == current_user.id
    ).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(review, field, value)

    db.commit()
    db.refresh(review)
    return review

# ── Delete own review ──────────────────────────────────
@router.delete("/{review_id}")
def delete_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    review = db.query(Review).filter(
        Review.id == review_id,
        Review.user_id == current_user.id
    ).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    db.delete(review)
    db.commit()
    return {"message": "Review deleted"}