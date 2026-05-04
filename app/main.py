from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.database import Base, engine

# ── Import ALL models here so SQLAlchemy registers them ──
from app.models import user, course, lecture, enrollment, cart, order, review, chat

# ── Import routers ────────────────────────────────────
from app.routers import auth, courses, lectures, cart, payments, chat

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Course Marketplace API", version="1.0.0")

app.add_middleware(SessionMiddleware, secret_key="your_session_secret")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(lectures.router)
app.include_router(cart.router)
app.include_router(payments.router)
app.include_router(chat.router)

@app.get("/")
def root():
    return {"message": "Course Marketplace API is running"}