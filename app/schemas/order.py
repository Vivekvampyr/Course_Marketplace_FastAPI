from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.models.order import OrderStatus

class OrderItemResponse(BaseModel):
    id: int
    course_id: int
    price: float

    class Config:
        from_attributes = True

class OrderResponse(BaseModel):
    id: int
    total_amount: float
    status: OrderStatus
    razorpay_order_id: Optional[str]
    created_at: datetime
    items: List[OrderItemResponse] = []

    class Config:
        from_attributes = True

class RazorpayOrderResponse(BaseModel):
    razorpay_order_id: str
    amount: int           # In paise (multiply by 100)
    currency: str
    order_id: int         # Our DB order id

class PaymentVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str