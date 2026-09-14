import os
import shutil
from fastapi import APIRouter, UploadFile, Form, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.services.downloader import download_audio_from_youtube, save_uploaded_file, VIDEO_EXTENSIONS
from app.services.transcriber import transcribe_audio
from app.services.corrector import correct_lines
from app.services.subtitle_writer import write_subtitle_file
from app.services.video_burner import burn_subtitles_into_video
from app.services.media import media_duration_seconds
from app.services.usage import user_can_process_video, reserve_usage, videos_used_today
from app.models.schemas import CaptionResult
from app.models.db_models import User
from app.auth import get_current_user
from app.database import get_db
from app.config import settings

router = APIRouter(prefix="/captions", tags=["captions"])
SUPPORTED_LANGUAGES = ("sindhi", "urdu", "english")
ALLOWED_FORMATS = ("srt", "vtt")


@router.post("/from-upload", response_model=CaptionResult)
async def create_captions_from_upload(
    file: UploadFile,
    target_language: str = Form(...),
    export_format: str = Form("srt"),
    burn_video: bool = Form(True),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user_can_process_video(db, user):
        raise HTTPException(status_code=402, detail=f"Free daily limit reached ({settings.free_daily_videos} videos/day). Subscribe for unlimited.")
    target_language = target_language.lower().strip()
    export_format = export_format.lower().strip()
    if target_language not in SUPPORTED_LANGUAGES or export_format not in ALLOWED_FORMATS:
        raise HTTPException(status_code=400, detail="Invalid language or export format")
    if not file.filename:
        raise HTTPException(status_code=400, detail="Choose a file")
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(file_bytes) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb}MB limit")
    try:
        job_id, saved_path = save_uploaded_file(file_bytes, file.filename)
        duration = media_duration_seconds(saved_path)
        if duration > settings.free_tier_max_minutes * 60 and not user.is_subscribed:
            shutil.rmtree(os.path.dirname(saved_path), ignore_errors=True)
            raise HTTPException(status_code=402, detail=f"Free tier is limited to {settings.free_tier_max_minutes} minutes per video")
        if not user_can_process_video(db, user):
            shutil.rmtree(os.path.dirname(saved_path), ignore_errors=True)
            raise HTTPException(status_code=402, detail="Daily limit reached")
        reserve_usage(db, user, job_id)
        try:
            return _run_pipeline(saved_path, job_id, target_language, export_format, burn_video=burn_video and os.path.splitext(saved_path)[1].lower() in VIDEO_EXTENSIONS)
        except Exception:
            shutil.rmtree(os.path.dirname(saved_path), ignore_errors=True)
            raise
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Processing failed. Please try again.") from e


@router.post("/from-youtube", response_model=CaptionResult)
def create_captions_from_youtube(
    youtube_url: str = Form(...), target_language: str = Form(...), export_format: str = Form("srt"),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    if not user_can_process_video(db, user):
        raise HTTPException(status_code=402, detail=f"Free daily limit reached ({settings.free_daily_videos} videos/day). Subscribe for unlimited.")
    target_language = target_language.lower().strip(); export_format = export_format.lower().strip()
    if target_language not in SUPPORTED_LANGUAGES or export_format not in ALLOWED_FORMATS:
        raise HTTPException(status_code=400, detail="Invalid language or export format")
    try:
        job_id, audio_path = download_audio_from_youtube(youtube_url)
        duration = media_duration_seconds(audio_path)
        if duration > settings.free_tier_max_minutes * 60 and not user.is_subscribed:
            shutil.rmtree(os.path.dirname(audio_path), ignore_errors=True)
            raise HTTPException(status_code=402, detail=f"Free tier is limited to {settings.free_tier_max_minutes} minutes per video")
        reserve_usage(db, user, job_id)
        try:
            return _run_pipeline(audio_path, job_id, target_language, export_format, burn_video=False)
        except Exception:
            shutil.rmtree(os.path.dirname(audio_path), ignore_errors=True)
            raise
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="YouTube processing failed. Please check the URL and try again.") from e


@router.get("/usage")
def usage_today(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    used = videos_used_today(db, user)
    active = bool(user.is_subscribed and (not user.subscription_expires_at or user.subscription_expires_at > __import__('datetime').datetime.utcnow()))
    return {"used_today": used, "daily_limit": None if active else settings.free_daily_videos, "is_subscribed": active}


@router.get("/download/{job_id}/{filename}")
def download_caption_file(job_id: str, filename: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models.db_models import UsageRecord
    owns = db.query(UsageRecord).filter(UsageRecord.user_id == user.id, UsageRecord.job_id == job_id).first()
    if not owns:
        raise HTTPException(status_code=403, detail="You do not own this job")
    if os.path.basename(job_id) != job_id or os.path.basename(filename) != filename:
        raise HTTPException(status_code=400, detail="Invalid file path")
    path = os.path.abspath(os.path.join(settings.storage_dir, job_id, filename))
    root = os.path.abspath(os.path.join(settings.storage_dir, job_id))
    if not path.startswith(root + os.sep) or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)


def _run_pipeline(source_path, job_id, target_language, export_format, burn_video=False):
    out_dir = os.path.dirname(source_path)
    raw_lines = transcribe_audio(source_path)
    if not raw_lines:
        raise ValueError("No speech was detected in the media")
    corrected = correct_lines(raw_lines, target_language)
    subtitle_path = write_subtitle_file(corrected, out_dir, "srt" if burn_video else export_format)
    video_download_path = None
    if burn_video:
        try:
            video_path = burn_subtitles_into_video(source_path, subtitle_path, out_dir)
            video_download_path = f"/captions/download/{job_id}/{os.path.basename(video_path)}"
        except RuntimeError:
            video_download_path = None
    return CaptionResult(job_id=job_id, language=target_language, export_format=export_format,
        download_path=f"/captions/download/{job_id}/{os.path.basename(subtitle_path)}",
        line_count=len(corrected), video_download_path=video_download_path)
