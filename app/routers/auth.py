from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from app.database import get_db
from app.schemas.user import UserRegister, UserLogin, TokenResponse, RefreshTokenRequest
from app.services.auth_service import (
    register_user, login_user,
    refresh_access_token, get_or_create_google_user
)
from app.utils.jwt import create_access_token, create_refresh_token
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Auth"])

# Google OAuth setup
config = Config(environ={
    "GOOGLE_CLIENT_ID": settings.GOOGLE_CLIENT_ID,
    "GOOGLE_CLIENT_SECRET": settings.GOOGLE_CLIENT_SECRET,
})
oauth = OAuth(config)
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# ── Register ──────────────────────────────────────────
@router.post("/register", response_model=TokenResponse)
def register(data: UserRegister, db: Session = Depends(get_db)):
    user = register_user(data, db)
    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, user=user)

# ── Login ─────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    access_token, refresh_token, user = login_user(data.email, data.password, db)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, user=user)

# ── Refresh Token ─────────────────────────────────────
@router.post("/refresh")
def refresh(data: RefreshTokenRequest, db: Session = Depends(get_db)):
    access_token, user = refresh_access_token(data.refresh_token, db)
    return {"access_token": access_token, "token_type": "bearer"}

# ── Google OAuth ──────────────────────────────────────
@router.get("/google")
async def google_login(request: Request):
    return await oauth.google.authorize_redirect(request, settings.GOOGLE_REDIRECT_URI)

@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    token = await oauth.google.authorize_access_token(request)
    google_user = token.get("userinfo")
    user = get_or_create_google_user(dict(google_user), db)
    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    # In production → redirect to Flutter app with tokens
    return {"access_token": access_token, "refresh_token": refresh_token, "user": user.email}