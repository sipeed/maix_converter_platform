import asyncio
import json
import os
import re
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from shutil import copyfileobj, rmtree

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from converter.yolo.node_profiles import get_yolo_profile


BASE_DIR = Path(__file__).resolve().parents[1]
JOBS_DIR = BASE_DIR / "jobs"
STATIC_DIR = Path(__file__).resolve().parent / "static"
MODEL_SUFFIXES = {".pt", ".onnx"}
DATASET_SUFFIXES = {".zip"}

app = FastAPI(title="Maix Converter Platform")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/jobs")
def create_job(
    model: UploadFile = File(...),
    dataset: UploadFile = File(...),
    model_name: str = Form(""),
    images_num: int = Form(100),
    imgsz_width: int = Form(640),
    imgsz_height: int = Form(480),
    yolo_version: str = Form("yolo26"),
    fast: bool = Form(False),
):
    if images_num < 1 or images_num > 5000:
        raise HTTPException(status_code=400, detail="images_num must be between 1 and 5000")
    validate_imgsz(imgsz_width, imgsz_height)

    model_suffix = Path(model.filename or "").suffix.lower()
    dataset_suffix = Path(dataset.filename or "").suffix.lower()
    if model_suffix not in MODEL_SUFFIXES:
        raise HTTPException(status_code=400, detail="model must be .pt or .onnx")
    if dataset_suffix not in DATASET_SUFFIXES:
        raise HTTPException(status_code=400, detail="dataset upload must be .zip")

    clean_model_name = slugify(model_name) or slugify(Path(model.filename or "model").stem)
    if not clean_model_name:
        raise HTTPException(status_code=400, detail="model_name is required")
    try:
        profile = get_yolo_profile(yolo_version, "detect")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job_id = new_job_id(clean_model_name, yolo_version=profile.yolo_version)
    job_dir = JOBS_DIR / job_id
    upload_dir = job_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=False)

    model_path = upload_dir / f"{clean_model_name}{model_suffix}"
    dataset_path = upload_dir / f"dataset{dataset_suffix}"
    try:
        save_upload(model, model_path)
        save_upload(dataset, dataset_path)
    except Exception as exc:
        rmtree(job_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"failed to save upload: {exc}") from exc

    write_json(
        job_dir / "job.json",
        {
            "status": "queued",
            "created_at": now_iso(),
            "job_id": job_id,
            "model_name": clean_model_name,
            "yolo_version": profile.yolo_version,
            "task": profile.task,
            "input_model": str(model_path),
            "dataset": str(dataset_path),
            "images_num": images_num,
            "imgsz": [imgsz_width, imgsz_height],
            "output_nodes": profile.output_names,
            "fast": fast,
            "api_log": str(job_dir / "api.log"),
        },
    )

    thread = threading.Thread(
        target=run_conversion,
        kwargs={
            "job_dir": job_dir,
            "model_path": model_path,
            "dataset_path": dataset_path,
            "model_name": clean_model_name,
            "yolo_version": profile.yolo_version,
            "images_num": images_num,
            "imgsz_width": imgsz_width,
            "imgsz_height": imgsz_height,
            "fast": fast,
        },
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id, "status": "queued", "job": f"/api/jobs/{job_id}"}


@app.get("/api/jobs")
def list_jobs():
    return {"jobs": read_jobs_list()}


@app.get("/api/jobs/events")
async def stream_jobs(request: Request):
    async def events():
        last_payload = ""
        idle_ticks = 0
        while True:
            if await request.is_disconnected():
                return

            payload = json.dumps({"jobs": read_jobs_list()}, ensure_ascii=False, sort_keys=True)
            if payload != last_payload:
                yield f"event: jobs\ndata: {payload}\n\n"
                last_payload = payload
                idle_ticks = 0
            else:
                idle_ticks += 1
                if idle_ticks >= 15:
                    yield ": keep-alive\n\n"
                    idle_ticks = 0

            await asyncio.sleep(1.0)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    return read_job_json(get_job_dir(job_id))


@app.get("/api/jobs/{job_id}/log", response_class=PlainTextResponse)
def get_job_log(job_id: str):
    job_dir = get_job_dir(job_id)
    chunks = []
    for name in ["api.log", "convert.log"]:
        path = job_dir / name
        if path.exists():
            chunks.append(f"===== {name} =====\n{path.read_text(encoding='utf-8', errors='replace')}")
    if not chunks:
        return ""
    return "\n\n".join(chunks)


@app.get("/api/jobs/{job_id}/download")
def download_job(job_id: str):
    job_dir = get_job_dir(job_id)
    job = read_job_json(job_dir)
    zip_path = Path(job.get("zip", ""))
    if not is_relative_to(zip_path.resolve(), job_dir.resolve()):
        raise HTTPException(status_code=400, detail="invalid result zip path")
    if not zip_path.is_file():
        raise HTTPException(status_code=404, detail="result zip is not ready")
    return FileResponse(zip_path, filename=zip_path.name)


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str):
    job_dir = get_job_dir(job_id)
    try:
        job = read_job_json(job_dir)
    except HTTPException as exc:
        if exc.status_code != 404:
            raise
        job = {"status": "unknown", "docker_image": "pulsar2:6.0"}
    if job.get("status") in {"queued", "running"}:
        raise HTTPException(status_code=409, detail="cannot delete a queued or running job")
    remove_job_dir(job_dir, docker_image=job.get("docker_image", "pulsar2:6.0"))
    return {"deleted": True, "job_id": job_id}


@app.websocket("/api/jobs/{job_id}/stream")
async def stream_job(websocket: WebSocket, job_id: str):
    await websocket.accept()
    try:
        job_dir = get_job_dir(job_id)
    except HTTPException as exc:
        await websocket.send_json({"type": "error", "message": exc.detail})
        await websocket.close()
        return

    offsets = {"api.log": 0, "convert.log": 0}
    last_status = None
    last_job_mtime = 0.0

    try:
        while True:
            try:
                job = read_job_json(job_dir)
                job_mtime = (job_dir / "job.json").stat().st_mtime
            except HTTPException as exc:
                await websocket.send_json({"type": "error", "message": exc.detail})
                await websocket.close()
                return
            except FileNotFoundError:
                await websocket.send_json({"type": "error", "message": "job was deleted"})
                await websocket.close()
                return
            if job.get("status") != last_status or job_mtime != last_job_mtime:
                await websocket.send_json({"type": "job", "job": job})
                last_status = job.get("status")
                last_job_mtime = job_mtime

            log_names = ["convert.log"] if (job_dir / "convert.log").exists() else ["api.log"]
            for name in log_names:
                path = job_dir / name
                if not path.exists():
                    continue
                size = path.stat().st_size
                if size < offsets[name]:
                    offsets[name] = 0
                if size > offsets[name]:
                    with path.open("r", encoding="utf-8", errors="replace") as f:
                        f.seek(offsets[name])
                        chunk = f.read()
                        offsets[name] = f.tell()
                    if chunk:
                        await websocket.send_json({"type": "log", "name": name, "text": chunk})

            if job.get("status") in {"success", "failed"}:
                await websocket.send_json({"type": "done", "status": job.get("status")})
                await websocket.close()
                return

            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        return


def run_conversion(
    *,
    job_dir: Path,
    model_path: Path,
    dataset_path: Path,
    model_name: str,
    yolo_version: str,
    images_num: int,
    imgsz_width: int,
    imgsz_height: int,
    fast: bool,
) -> None:
    cmd = [
        sys.executable,
        str(BASE_DIR / "convert_cli.py"),
        "--model",
        str(model_path),
        "--dataset",
        str(dataset_path),
        "--model-name",
        model_name,
        "--yolo-version",
        yolo_version,
        "--imgsz",
        str(imgsz_width),
        str(imgsz_height),
        "--images-num",
        str(images_num),
        "--job-dir",
        str(job_dir),
    ]
    if fast:
        cmd.append("--fast")

    api_log = job_dir / "api.log"
    with api_log.open("w", encoding="utf-8") as log:
        log.write("+ " + " ".join(cmd) + "\n")
        log.flush()
        result = subprocess.run(
            cmd,
            cwd=BASE_DIR,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            ensure_failed_job(job_dir, f"converter exited with code {result.returncode}")


def save_upload(upload: UploadFile, path: Path) -> None:
    with path.open("wb") as f:
        copyfileobj(upload.file, f)


def remove_job_dir(job_dir: Path, docker_image: str) -> None:
    try:
        rmtree(job_dir)
        return
    except PermissionError:
        repair_job_owner_with_docker(job_dir, docker_image=docker_image)

    try:
        rmtree(job_dir)
    except PermissionError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"failed to delete job because some files are not writable: {exc}",
        ) from exc


def repair_job_owner_with_docker(job_dir: Path, docker_image: str) -> None:
    uid = os.getuid()
    gid = os.getgid()
    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{job_dir.resolve()}:/data",
        "--entrypoint",
        "/bin/chown",
        docker_image,
        "-R",
        f"{uid}:{gid}",
        "/data",
    ]
    result = subprocess.run(
        cmd,
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail="failed to repair Docker-generated file permissions before delete:\n" + result.stdout,
        )


def read_job_summary(job_dir: Path) -> dict:
    try:
        job = read_job_json(job_dir)
    except HTTPException:
        job = {"status": "unknown"}
    job.setdefault("job_id", job_dir.name)
    return {
        "job_id": job["job_id"],
        "status": job.get("status", "unknown"),
        "model_name": job.get("model_name", ""),
        "yolo_version": job.get("yolo_version", ""),
        "created_at": job.get("created_at", ""),
        "completed_at": job.get("completed_at", ""),
    }


def read_jobs_list() -> list[dict]:
    jobs = []
    if JOBS_DIR.exists():
        for path in sorted(JOBS_DIR.iterdir(), reverse=True):
            if path.is_dir():
                jobs.append(read_job_summary(path))
    return jobs


def read_job_json(job_dir: Path) -> dict:
    path = job_dir / "job.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="job metadata not found")
    with path.open("r", encoding="utf-8") as f:
        job = json.load(f)
    job.setdefault("job_id", job_dir.name)
    return job


def get_job_dir(job_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", job_id):
        raise HTTPException(status_code=400, detail="invalid job_id")
    job_dir = JOBS_DIR / job_id
    if not job_dir.is_dir():
        raise HTTPException(status_code=404, detail="job not found")
    return job_dir


def write_json(path: Path, data: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def new_job_id(model_name: str, yolo_version: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"{stamp}_{model_name}_maixcam2_{yolo_version}"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def slugify(value: str) -> str:
    value = value.strip()
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
    return value.strip("._-")[:80]


def validate_imgsz(width: int, height: int) -> None:
    for name, value in [("imgsz_width", width), ("imgsz_height", height)]:
        if value < 32 or value > 4096:
            raise HTTPException(status_code=400, detail=f"{name} must be between 32 and 4096")
        if value % 32 != 0:
            raise HTTPException(status_code=400, detail=f"{name} must be a multiple of 32")


def is_relative_to(path: Path, root: Path) -> bool:
    return root == path or root in path.parents


def ensure_failed_job(job_dir: Path, error: str) -> None:
    try:
        job = read_job_json(job_dir)
    except HTTPException:
        job = {"job_id": job_dir.name, "created_at": now_iso()}
    if job.get("status") in {"success", "failed"}:
        return
    job.update({"status": "failed", "completed_at": now_iso(), "error": error})
    write_json(job_dir / "job.json", job)
