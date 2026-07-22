import re
from pathlib import Path


CANCEL_MARKER_NAME = ".cancel_requested"


def docker_container_name(job_dir: Path) -> str:
    safe_job_id = re.sub(r"[^A-Za-z0-9_.-]+", "-", job_dir.name).strip(".-") or "job"
    return f"maix-converter-{safe_job_id}"[:120]


def request_cancel(job_dir: Path) -> None:
    (job_dir / CANCEL_MARKER_NAME).touch(exist_ok=True)


def is_cancel_requested(job_dir: Path) -> bool:
    return (job_dir / CANCEL_MARKER_NAME).exists()
