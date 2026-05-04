from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine

# Import routers (we'll add these as we build)
# from app.routers import auth, users, courses, lectures, cart, orders, payments, reviews, chat

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Course Marketplace API",
    description="Backend for Online Course Marketplace",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded files (videos, thumbnails)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
def root():
    return {"message": "Course Marketplace API is running"}