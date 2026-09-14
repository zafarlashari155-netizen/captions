"""
Step 5 (optional) of the pipeline: burn the subtitle file directly into
the video frames, for apps (like this one) whose UI promises a single
downloadable captioned video rather than a separate .srt/.vtt file.

Requires ffmpeg to be installed on the server (apt install ffmpeg, or
already present on most Render/Railway base images — check with
`ffmpeg -version` after deploy and add a build step if it's missing).
"""

import os
import subprocess


def burn_subtitles_into_video(video_path: str, srt_path: str, out_dir: str) -> str:
    output_path = os.path.join(out_dir, "captioned_video.mp4")

    # ffmpeg's subtitles filter needs a path with no special characters
    # that would break its internal escaping — copying to a plain name
    # inside the same job folder avoids that.
    safe_srt_path = os.path.join(out_dir, "captions_for_burn.srt")
    if srt_path != safe_srt_path:
        with open(srt_path, "r", encoding="utf-8") as src, open(safe_srt_path, "w", encoding="utf-8") as dst:
            dst.write(src.read())

    command = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", f"subtitles={safe_srt_path}:force_style='FontSize=20,PrimaryColour=&HFFFFFF&'",
        "-c:a", "copy",
        output_path,
    ]

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr[-800:]}")

    return output_path
