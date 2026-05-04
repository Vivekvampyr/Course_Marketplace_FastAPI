from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.cart import Cart
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.schemas.cart import CartAddRequest, CartItemResponse
from app.dependencies.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/cart", tags=["Cart"])

# ── View cart ──────────────────────────────────────────
@router.get("/", response_model=List[CartItemResponse])
def get_cart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(Cart).filter(Cart.user_id == current_user.id).all()

# ── Add to cart ────────────────────────────────────────
@router.post("/add")
def add_to_cart(
    data: CartAddRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check course exists and is published
    course = db.query(Course).filter(
        Course.id == data.course_id,
        Course.is_published == True
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Check already enrolled
    enrolled = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.course_id == data.course_id
    ).first()
    if enrolled:
        raise HTTPException(status_code=400, detail="Already enrolled in this course")

    # Check already in cart
    in_cart = db.query(Cart).filter(
        Cart.user_id == current_user.id,
        Cart.course_id == data.course_id
    ).first()
    if in_cart:
        raise HTTPException(status_code=400, detail="Course already in cart")

    cart_item = Cart(user_id=current_user.id, course_id=data.course_id)
    db.add(cart_item)
    db.commit()
    return {"message": "Course added to cart"}

# ── Remove from cart ───────────────────────────────────
@router.delete("/remove/{course_id}")
def remove_from_cart(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    item = db.query(Cart).filter(
        Cart.user_id == current_user.id,
        Cart.course_id == course_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not in cart")

    db.delete(item)
    db.commit()
    return {"message": "Removed from cart"}

# ── Clear cart ─────────────────────────────────────────
@router.delete("/clear")
def clear_cart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db.query(Cart).filter(Cart.user_id == current_user.id).delete()
    db.commit()
    return {"message": "Cart cleared"}