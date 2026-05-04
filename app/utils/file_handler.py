import os
import shutil

def delete_file(file_path: str):
    if file_path and os.path.exists(file_path):
        os.remove(file_path)

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def save_upload(file, destination: str) -> str:
    ensure_dir(os.path.dirname(destination))
    with open(destination, "wb") as f:
        shutil.copyfileobj(file, f)
    return destination