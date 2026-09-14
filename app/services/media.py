import subprocess


def media_duration_seconds(path: str) -> float:
    result = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path
    ], capture_output=True, text=True)
    if result.returncode != 0:
        raise ValueError("Invalid or unreadable media file")
    try:
        duration = float(result.stdout.strip())
    except ValueError:
        raise ValueError("Could not determine media duration")
    if duration <= 0:
        raise ValueError("Media has no usable duration")
    return duration
