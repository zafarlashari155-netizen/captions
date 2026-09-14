"""
Step 2 of the pipeline: turn the audio file into a raw, timestamped
transcript. This step is language-agnostic — it captures whatever is
spoken (Sindhi, Urdu, English, or a mix). Correction into clean
Sindhi/Urdu script happens later, in corrector.py.
"""

from openai import OpenAI
from app.config import settings
from app.models.schemas import CaptionLine

client = OpenAI(api_key=settings.openai_api_key)


def transcribe_audio(audio_path: str) -> list[CaptionLine]:
    with open(audio_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )

    lines = []
    for i, segment in enumerate(response.segments):
        lines.append(
            CaptionLine(
                index=i + 1,
                start_seconds=segment.start,
                end_seconds=segment.end,
                text=segment.text.strip(),
            )
        )
    return lines
