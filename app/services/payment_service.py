import razorpay
import hmac
import hashlib
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.config import settings
from app.models.order import Order, OrderItem, OrderStatus
from app.models.cart import Cart
from app.models.course import Course
from app.models.enrollment import Enrollment

# Initialize Razorpay client
client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

def create_razorpay_order(user_id: int, db: Session):
    # Get user's cart items
    cart_items = db.query(Cart).filter(Cart.user_id == user_id).all()
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # Check already enrolled
    for item in cart_items:
        already_enrolled = db.query(Enrollment).filter(
            Enrollment.user_id == user_id,
            Enrollment.course_id == item.course_id
        ).first()
        if already_enrolled:
            raise HTTPException(
                status_code=400,
                detail=f"Already enrolled in course {item.course_id}"
            )

    # Calculate total
    total = 0.0
    course_prices = []
    for item in cart_items:
        course = db.query(Course).filter(Course.id == item.course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail=f"Course {item.course_id} not found")
        total += course.price
        course_prices.append((course.id, course.price))

    # Create order in DB
    order = Order(
        user_id=user_id,
        total_amount=total,
        status=OrderStatus.pending
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    # Add order items
    for course_id, price in course_prices:
        order_item = OrderItem(
            order_id=order.id,
            course_id=course_id,
            price=price
        )
        db.add(order_item)

    # Create Razorpay order (amount in paise)
    razorpay_order = client.order.create({
        "amount": int(total * 100),
        "currency": "INR",
        "receipt": f"order_{order.id}",
        "payment_capture": 1
    })

    # Save Razorpay order ID
    order.razorpay_order_id = razorpay_order["id"]
    db.commit()
    db.refresh(order)

    return {
        "razorpay_order_id": razorpay_order["id"],
        "amount": int(total * 100),
        "currency": "INR",
        "order_id": order.id
    }


def verify_payment(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
    db: Session
):
    # Step 1 — Verify signature
    body = razorpay_order_id + "|" + razorpay_payment_id
    expected_signature = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        body.encode(),
        hashlib.sha256
    ).hexdigest()

    if expected_signature != razorpay_signature:
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    # Step 2 — Find order
    order = db.query(Order).filter(
        Order.razorpay_order_id == razorpay_order_id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Step 3 — Mark as paid
    order.status = OrderStatus.paid
    order.razorpay_payment_id = razorpay_payment_id
    order.razorpay_signature = razorpay_signature
    db.commit()

    # Step 4 — Enroll user in all purchased courses
    for item in order.items:
        existing = db.query(Enrollment).filter(
            Enrollment.user_id == order.user_id,
            Enrollment.course_id == item.course_id
        ).first()
        if not existing:
            enrollment = Enrollment(
                user_id=order.user_id,
                course_id=item.course_id
            )
            db.add(enrollment)

    # Step 5 — Clear cart
    db.query(Cart).filter(Cart.user_id == order.user_id).delete()
    db.commit()

    return {"message": "Payment verified. Enrolled successfully!", "order_id": order.id}