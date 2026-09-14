import os
import re
import shutil
import uuid
import yt_dlp
from app.config import settings

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
ALLOWED_UPLOAD_EXTENSIONS = VIDEO_EXTENSIONS | {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}


def _new_job_dir():
    job_id = str(uuid.uuid4())
    out_dir = os.path.abspath(os.path.join(settings.storage_dir, job_id))
    os.makedirs(out_dir, exist_ok=False)
    return job_id, out_dir


def validate_youtube_url(url: str) -> str:
    url = (url or "").strip()
    if not re.match(r"^https?://(www\.)?(youtube\.com|youtu\.be)/", url, re.I):
        raise ValueError("Only YouTube URLs are supported")
    return url


def download_audio_from_youtube(youtube_url: str) -> tuple[str, str]:
    youtube_url = validate_youtube_url(youtube_url)
    job_id, out_dir = _new_job_dir()
    out_template = os.path.join(out_dir, "source.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "noplaylist": True,
        "restrictfilenames": True,
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
        "quiet": True,
        "no_warnings": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
    except Exception:
        shutil.rmtree(out_dir, ignore_errors=True)
        raise
    path = os.path.join(out_dir, "source.mp3")
    if not os.path.isfile(path):
        shutil.rmtree(out_dir, ignore_errors=True)
        raise RuntimeError("YouTube audio download failed")
    return job_id, path


def save_uploaded_file(file_bytes: bytes, original_filename: str) -> tuple[str, str]:
    ext = os.path.splitext(original_filename or "")[1].lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise ValueError("Unsupported file format")
    job_id, out_dir = _new_job_dir()
    dest_path = os.path.join(out_dir, f"source{ext}")
    with open(dest_path, "wb") as f:
        f.write(file_bytes)
    return job_id, dest_path
