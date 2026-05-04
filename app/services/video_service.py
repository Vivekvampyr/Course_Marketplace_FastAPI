import os
import aiofiles
from fastapi import UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from app.config import settings

ALLOWED_VIDEO_TYPES = ["video/mp4", "video/webm", "video/mkv", "video/avi"]
MAX_VIDEO_SIZE_MB = 500  # 500MB limit

def get_video_path(course_id: int, lecture_id: int, filename: str) -> str:
    folder = os.path.join(settings.UPLOAD_DIR, "videos", str(course_id))
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{lecture_id}_{filename}")

async def save_video(file: UploadFile, course_id: int, lecture_id: int) -> str:
    if file.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(status_code=400, detail="Invalid video format. Use mp4, webm, mkv.")

    file_path = get_video_path(course_id, lecture_id, file.filename)

    async with aiofiles.open(file_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # Read 1MB chunks
            await f.write(chunk)

    return file_path

def delete_video(video_path: str):
    if video_path and os.path.exists(video_path):
        os.remove(video_path)

async def stream_video(video_path: str, range_header: str = None) -> StreamingResponse:
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video not found")

    file_size = os.path.getsize(video_path)
    chunk_size = 1024 * 1024  # 1MB per chunk

    # Handle HTTP Range requests (seek support)
    if range_header:
        range_val = range_header.replace("bytes=", "")
        start_str, end_str = range_val.split("-")
        start = int(start_str)
        end = int(end_str) if end_str else file_size - 1
    else:
        start = 0
        end = file_size - 1

    content_length = end - start + 1

    async def video_generator():
        async with aiofiles.open(video_path, "rb") as f:
            await f.seek(start)
            remaining = content_length
            while remaining > 0:
                read_size = min(chunk_size, remaining)
                data = await f.read(read_size)
                if not data:
                    break
                yield data
                remaining -= len(data)

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Type": "video/mp4",
    }

    status_code = 206 if range_header else 200
    return StreamingResponse(video_generator(), status_code=status_code, headers=headers)