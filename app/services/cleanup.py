import os
import shutil
import time
from app.config import settings


def cleanup_old_jobs(max_age_hours: int = 24) -> int:
    root = os.path.abspath(settings.storage_dir)
    os.makedirs(root, exist_ok=True)
    cutoff = time.time() - max_age_hours * 3600
    removed = 0
    for name in os.listdir(root):
        path = os.path.join(root, name)
        if os.path.isdir(path) and os.path.getmtime(path) < cutoff:
            shutil.rmtree(path, ignore_errors=True)
            removed += 1
    return removed
