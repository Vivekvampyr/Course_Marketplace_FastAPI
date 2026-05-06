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
        raise HTTPException(status_code=400, detail="Invalid video format.")

    file_path = get_video_path(course_id, lecture_id, file.filename)

    async with aiofiles.open(file_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            await f.write(chunk)

    # ← Fix: always return forward slashes
    return file_path.replace("\\", "/")

def delete_video(video_path: str):
    if video_path and os.path.exists(video_path):
        os.remove(video_path)

async def stream_video(video_path: str, range_header: str = None) -> StreamingResponse:
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video not found")

    file_size  = os.path.getsize(video_path)
    chunk_size = 1024 * 1024  # 1MB

    if range_header:
        try:
            range_val  = range_header.replace("bytes=", "")
            parts      = range_val.split("-")
            start      = int(parts[0]) if parts[0] else 0
            end        = int(parts[1]) if parts[1] else file_size - 1
        except Exception:
            start = 0
            end   = file_size - 1
    else:
        start = 0
        end   = file_size - 1

    # Clamp values
    start          = max(0, min(start, file_size - 1))
    end            = max(start, min(end, file_size - 1))
    content_length = end - start + 1

    async def video_generator():
        async with aiofiles.open(video_path, "rb") as f:
            await f.seek(start)
            remaining = content_length
            while remaining > 0:
                read_size = min(chunk_size, remaining)
                data      = await f.read(read_size)
                if not data:
                    break
                yield data
                remaining -= len(data)

    headers = {
        "Content-Range":  f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges":  "bytes",
        "Content-Length": str(content_length),
        "Content-Type":   "video/mp4",
    }

    return StreamingResponse(
        video_generator(),
        status_code=206 if range_header else 200,
        headers=headers
    )