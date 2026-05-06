# run this command to start the server: uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.database import Base, engine

# ── All models must be imported before create_all ─────
from app.models import user, course, lecture, enrollment, cart, order, review, chat

# ── Routers ───────────────────────────────────────────
from app.routers import auth, users, courses, lectures, cart, payments, reviews, chat

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Course Marketplace API",
    description="Online Course Marketplace Backend",
    version="1.0.0"
)

app.add_middleware(SessionMiddleware, secret_key="your_session_secret")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(courses.router)
app.include_router(lectures.router)
app.include_router(cart.router)
app.include_router(payments.router)
app.include_router(reviews.router)
app.include_router(chat.router)

@app.get("/")
def root():
    return {
        "message": "Course Marketplace API",
        "docs": "/docs",
        "version": "1.0.0"
    }