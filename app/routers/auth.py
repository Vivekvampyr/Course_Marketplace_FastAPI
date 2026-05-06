from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from fastapi.security import OAuth2PasswordRequestForm

import httpx

from app.database import get_db
from app.schemas.user import UserRegister, UserLogin, TokenResponse, RefreshTokenRequest
from app.services.auth_service import (
    register_user, login_user,
    refresh_access_token, get_or_create_google_user
)
from app.utils.jwt import create_access_token, create_refresh_token
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Auth"])

# ── Google OAuth setup (Web browser flow) ─────────────
config = Config(environ={
    "GOOGLE_CLIENT_ID":     settings.GOOGLE_CLIENT_ID,
    "GOOGLE_CLIENT_SECRET": settings.GOOGLE_CLIENT_SECRET,
})
oauth = OAuth(config)
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# ── Register ───────────────────────────────────────────
@router.post("/register", response_model=TokenResponse)
def register(data: UserRegister, db: Session = Depends(get_db)):
    user = register_user(data, db)
    access_token  = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, user=user)

# ── Login ──────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    access_token, refresh_token, user = login_user(
        form_data.username,
        form_data.password,
        db
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user
    )

# ── Refresh Token ──────────────────────────────────────
@router.post("/refresh")
def refresh(data: RefreshTokenRequest, db: Session = Depends(get_db)):
    access_token, user = refresh_access_token(data.refresh_token, db)
    return {"access_token": access_token, "token_type": "bearer"}

# ── Google OAuth (Web browser flow) ───────────────────
@router.get("/google")
async def google_login(request: Request):
    return await oauth.google.authorize_redirect(request, settings.GOOGLE_REDIRECT_URI)

@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    token     = await oauth.google.authorize_access_token(request)
    google_user = token.get("userinfo")
    user      = get_or_create_google_user(dict(google_user), db)
    access_token  = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    return {"access_token": access_token, "refresh_token": refresh_token, "user": user.email}

# ── Google OAuth (Flutter Mobile + Web) ───────────────
@router.post("/google/mobile")
async def google_mobile_login(payload: dict, db: Session = Depends(get_db)):
    try:
        is_web = payload.get("is_web", False)

        if is_web:
            # Flutter Web sends accessToken → fetch user info from Google
            access_token = payload.get("access_token")
            if not access_token:
                raise HTTPException(status_code=400, detail="access_token required for web")

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
            if resp.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid Google access token")

            info = resp.json()
            google_data = {
                "sub":     info["sub"],
                "email":   info["email"],
                "name":    info.get("name", ""),
                "picture": info.get("picture", "")
            }

        else:
            # Flutter Android sends idToken → verify directly
            token_value = payload.get("id_token")
            if not token_value:
                raise HTTPException(status_code=400, detail="id_token required for Android")

            id_info = id_token.verify_oauth2_token(
                token_value,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID
            )
            google_data = {
                "sub":     id_info["sub"],
                "email":   id_info["email"],
                "name":    id_info.get("name", ""),
                "picture": id_info.get("picture", "")
            }

        # Create or fetch user from DB
        user          = get_or_create_google_user(google_data, db)
        access_token  = create_access_token({"sub": str(user.id), "role": user.role})
        refresh_token = create_refresh_token({"sub": str(user.id)})

        return {
            "access_token":  access_token,
            "refresh_token": refresh_token,
            "user": {
                "id":         user.id,
                "name":       user.name,
                "email":      user.email,
                "role":       user.role,
                "avatar":     user.avatar,
                "is_active":  user.is_active,
                "created_at": str(user.created_at)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Google auth failed: {str(e)}")