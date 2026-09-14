import os
from app.models.schemas import CaptionLine


def _timestamp(seconds: float, sep: str) -> str:
    total_ms = max(0, int(round(seconds * 1000)))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, millis = divmod(rem, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02}{sep}{millis:03}"


def _validate(lines):
    for line in lines:
        if line.end_seconds <= line.start_seconds:
            raise ValueError(f"Invalid caption timing at line {line.index}")


def write_srt(lines: list[CaptionLine], out_dir: str) -> str:
    _validate(lines)
    path = os.path.join(out_dir, "captions.srt")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for line in lines:
            f.write(f"{line.index}\n{_timestamp(line.start_seconds, ',')} --> {_timestamp(line.end_seconds, ',')}\n{line.text}\n\n")
    return path


def write_vtt(lines: list[CaptionLine], out_dir: str) -> str:
    _validate(lines)
    path = os.path.join(out_dir, "captions.vtt")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("WEBVTT\n\n")
        for line in lines:
            f.write(f"{_timestamp(line.start_seconds, '.')} --> {_timestamp(line.end_seconds, '.')}\n{line.text}\n\n")
    return path


def write_subtitle_file(lines: list[CaptionLine], out_dir: str, export_format: str) -> str:
    if export_format not in {"srt", "vtt"}:
        raise ValueError("Unsupported subtitle format")
    return write_vtt(lines, out_dir) if export_format == "vtt" else write_srt(lines, out_dir)
