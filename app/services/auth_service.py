from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User, UserRole
from app.schemas.user import UserRegister
from app.utils.hashing import hash_password, verify_password
from app.utils.jwt import create_access_token, create_refresh_token, decode_token

def register_user(data: UserRegister, db: Session):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=data.name,
        email=data.email,
        password=hash_password(data.password),
        role=data.role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def login_user(email: str, password: str, db: Session):
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    return access_token, refresh_token, user

def refresh_access_token(refresh_token: str, db: Session):
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.query(User).filter(User.id == int(payload.get("sub"))).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_access_token = create_access_token({"sub": str(user.id), "role": user.role})
    return new_access_token, user

def get_or_create_google_user(google_data: dict, db: Session):
    user = db.query(User).filter(User.email == google_data["email"]).first()

    if user:
        # Link google_id if not linked yet
        if not user.google_id:
            user.google_id = google_data["sub"]
            db.commit()
            db.refresh(user)
        return user

    # New user via Google
    user = User(
        name=google_data["name"],
        email=google_data["email"],
        google_id=google_data["sub"],
        avatar=google_data.get("picture"),
        is_verified=True,
        role=UserRole.student
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user