from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.order import RazorpayOrderResponse, PaymentVerifyRequest, OrderResponse
from app.services.payment_service import create_razorpay_order, verify_payment
from app.dependencies.auth import get_current_user
from app.models.order import Order
from app.models.user import User
from typing import List
import json
from app.config import settings

router = APIRouter(prefix="/payments", tags=["Payments"])

# ── Create Razorpay order from cart ───────────────────
@router.post("/create-order", response_model=RazorpayOrderResponse)
def create_order(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return create_razorpay_order(current_user.id, db)

# ── Verify payment after Razorpay checkout ────────────
@router.post("/verify")
def verify(
    data: PaymentVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return verify_payment(
        data.razorpay_order_id,
        data.razorpay_payment_id,
        data.razorpay_signature,
        db
    )

# ── Razorpay webhook (server-to-server) ───────────────
@router.post("/webhook")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET  # Set in Razorpay dashboard

    import hmac, hashlib
    signature = request.headers.get("x-razorpay-signature")
    expected = hmac.new(
        webhook_secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    if signature != expected:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    data = json.loads(payload)
    event = data.get("event")

    if event == "payment.captured":
        payment = data["payload"]["payment"]["entity"]
        order = db.query(Order).filter(
            Order.razorpay_order_id == payment["order_id"]
        ).first()
        if order:
            from app.models.order import OrderStatus
            order.status = OrderStatus.paid
            order.razorpay_payment_id = payment["id"]
            db.commit()

    return {"status": "ok"}

# ── Order history ──────────────────────────────────────
@router.get("/orders", response_model=List[OrderResponse])
def order_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(Order).filter(Order.user_id == current_user.id).all()