from typing import Literal
from pydantic import BaseModel


class CaptionRequest(BaseModel):
    source_path: str
    target_language: Literal["sindhi", "urdu", "english"]
    export_format: Literal["srt", "vtt"] = "srt"


class CaptionLine(BaseModel):
    index: int
    start_seconds: float
    end_seconds: float
    text: str


class CaptionResult(BaseModel):
    job_id: str
    language: str
    export_format: str
    download_path: str
    line_count: int
    video_download_path: str | None = None
