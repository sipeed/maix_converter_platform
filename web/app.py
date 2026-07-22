import asyncio
import hmac
import ipaddress
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from shutil import rmtree

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from converter.backends.maixcam2_pulsar2 import docker_bind_mount
from converter.common.job_control import docker_container_name, is_cancel_requested, request_cancel
from converter.common.names import sanitize_model_name
from converter.yolo.node_profiles import get_yolo_profile


def read_env_int(name: str, default: int, min_value: int = 0) -> int:
    value = os.getenv(name, "")
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return max(min_value, parsed)


BASE_DIR = Path(__file__).resolve().parents[1]
JOBS_DIR = BASE_DIR / "jobs"
RUNTIME_DIR = BASE_DIR / "runtime"
TEMP_DIR = RUNTIME_DIR / "tmp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(TEMP_DIR)
STATIC_DIR = Path(__file__).resolve().parent / "static"
MODEL_SUFFIXES = {".pt", ".onnx"}
DATASET_SUFFIXES = {".zip"}
TARGETS = {"maixcam2", "maixcam"}
JOB_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,180}")
FINISHED_STATUSES = {"success", "failed", "cancelled"}
ACTIVE_STATUSES = {"queued", "running"}
API_TOKEN = os.getenv("MAIX_API_TOKEN", "").strip()
AUTH_COOKIE_NAME = "maix_api_token"
UPLOAD_CHUNK_BYTES = 1024 * 1024
MAX_MODEL_UPLOAD_BYTES = read_env_int("MAIX_MAX_MODEL_MB", 1024, min_value=1) * 1024 * 1024
MAX_DATASET_UPLOAD_BYTES = read_env_int("MAIX_MAX_DATASET_MB", 4096, min_value=1) * 1024 * 1024
MAX_JOB_REQUEST_BYTES = MAX_MODEL_UPLOAD_BYTES + MAX_DATASET_UPLOAD_BYTES + 16 * 1024 * 1024
MAX_CONCURRENT_JOBS = read_env_int("MAIX_MAX_CONCURRENT_JOBS", 1, min_value=1)
MAX_LOG_RESPONSE_BYTES = read_env_int("MAIX_MAX_LOG_RESPONSE_MB", 8, min_value=1) * 1024 * 1024
MAX_API_LOG_BYTES = read_env_int("MAIX_MAX_API_LOG_MB", 64, min_value=1) * 1024 * 1024
LOG_STREAM_CHUNK_CHARS = 256 * 1024


@dataclass
class JobControl:
    process: subprocess.Popen | None = None
    future: Future | None = None
    cancel_requested: bool = False


job_controls: dict[str, JobControl] = {}
job_controls_lock = threading.Lock()
job_executor: ThreadPoolExecutor | None = None
JOBS_AUTO_CLEAN = os.getenv("MAIX_JOBS_AUTO_CLEAN", "1").lower() not in {"0", "false", "no", "off"}
JOBS_KEEP_DAYS = read_env_int("MAIX_JOBS_KEEP_DAYS", 7, min_value=0)
JOBS_KEEP_COUNT = read_env_int("MAIX_JOBS_KEEP_COUNT", 30, min_value=0)
JOBS_CLEAN_INTERVAL_SECONDS = read_env_int("MAIX_JOBS_CLEAN_INTERVAL_SECONDS", 21600, min_value=60)
cleanup_stop_event = threading.Event()
cleanup_thread: threading.Thread | None = None


class RequestBodyTooLarge(Exception):
    pass


class BodySizeLimitMiddleware:
    def __init__(self, app, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") != "http" or scope.get("method") != "POST" or scope.get("path") != "/api/jobs":
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        content_length = headers.get(b"content-length")
        if content_length:
            try:
                if int(content_length) > self.max_bytes:
                    await self.send_too_large(scope, receive, send)
                    return
            except ValueError:
                pass

        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message.get("type") == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise RequestBodyTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestBodyTooLarge:
            await self.send_too_large(scope, receive, send)

    async def send_too_large(self, scope, receive, send) -> None:
        response = JSONResponse(
            status_code=413,
            content={"detail": f"job upload exceeds the {self.max_bytes // (1024 * 1024)} MB request limit"},
        )
        await response(scope, receive, send)


app = FastAPI(title="Maix Converter Platform")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.middleware("http")
async def require_api_token(request: Request, call_next):
    if not request.url.path.startswith("/api/") or request.url.path == "/api/session":
        return await call_next(request)
    if not API_TOKEN:
        if is_loopback_client(request.client.host if request.client else ""):
            return await call_next(request)
        return JSONResponse(status_code=403, content={"detail": "remote API access requires MAIX_API_TOKEN"})
    if request_has_valid_token(request):
        return await call_next(request)
    return JSONResponse(
        status_code=401,
        content={"detail": "API token required"},
        headers={"WWW-Authenticate": "Bearer"},
    )


app.add_middleware(BodySizeLimitMiddleware, max_bytes=MAX_JOB_REQUEST_BYTES)


@app.on_event("startup")
def start_job_cleanup() -> None:
    global cleanup_thread, job_executor
    if job_executor is None:
        job_executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_JOBS, thread_name_prefix="conversion")
    reconcile_interrupted_jobs()
    if not JOBS_AUTO_CLEAN:
        return
    if cleanup_thread and cleanup_thread.is_alive():
        return
    cleanup_stop_event.clear()
    cleanup_thread = threading.Thread(target=job_cleanup_loop, name="job-cleanup", daemon=True)
    cleanup_thread.start()


@app.on_event("shutdown")
def stop_job_cleanup() -> None:
    global job_executor
    cleanup_stop_event.set()
    cancel_all_active_jobs("server is shutting down")
    if job_executor is not None:
        job_executor.shutdown(wait=True, cancel_futures=True)
        job_executor = None


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/session")
def create_api_session(request: Request, response: Response):
    if not API_TOKEN:
        if not is_loopback_client(request.client.host if request.client else ""):
            raise HTTPException(status_code=403, detail="remote API access requires MAIX_API_TOKEN")
        return {"authenticated": True, "required": False}
    token = extract_request_token(request)
    if not token or not hmac.compare_digest(token, API_TOKEN):
        raise HTTPException(status_code=401, detail="invalid API token")
    response.set_cookie(
        AUTH_COOKIE_NAME,
        API_TOKEN,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="strict",
    )
    return {"authenticated": True, "required": True}


@app.post("/api/jobs")
def create_job(
    model: UploadFile = File(...),
    dataset: UploadFile = File(...),
    model_name: str = Form(""),
    images_num: int = Form(100),
    imgsz_width: int = Form(640),
    imgsz_height: int = Form(480),
    target: str = Form("maixcam2"),
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
    target = target.lower()
    if target not in TARGETS:
        raise HTTPException(status_code=400, detail=f"unsupported target: {target}")

    clean_model_name = slugify(model_name) or slugify(Path(model.filename or "model").stem)
    if not clean_model_name:
        raise HTTPException(status_code=400, detail="model_name is required")
    try:
        profile = get_yolo_profile(yolo_version, "detect")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    docker_image = default_docker_image(target)
    job_id = new_job_id(clean_model_name, target=target, yolo_version=profile.yolo_version)
    job_dir = JOBS_DIR / job_id
    upload_dir = job_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=False)

    model_path = upload_dir / f"{clean_model_name}{model_suffix}"
    dataset_path = upload_dir / f"dataset{dataset_suffix}"
    try:
        save_upload(model, model_path, max_bytes=MAX_MODEL_UPLOAD_BYTES, label="model")
        save_upload(dataset, dataset_path, max_bytes=MAX_DATASET_UPLOAD_BYTES, label="dataset")
    except HTTPException:
        rmtree(job_dir, ignore_errors=True)
        raise
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
            "target": target,
            "yolo_version": profile.yolo_version,
            "task": profile.task,
            "input_model": str(model_path),
            "dataset": str(dataset_path),
            "images_num": images_num,
            "imgsz": [imgsz_width, imgsz_height],
            "requested_imgsz": [imgsz_width, imgsz_height],
            "output_nodes": profile.output_names,
            "fast": fast,
            "docker_image": docker_image,
            "docker_container": docker_container_name(job_dir),
            "api_log": str(job_dir / "api.log"),
        },
    )

    control = JobControl()
    with job_controls_lock:
        job_controls[job_id] = control
        executor = ensure_job_executor()
        future = executor.submit(
            run_conversion,
            job_id=job_id,
            job_dir=job_dir,
            model_path=model_path,
            dataset_path=dataset_path,
            model_name=clean_model_name,
            target=target,
            yolo_version=profile.yolo_version,
            images_num=images_num,
            imgsz_width=imgsz_width,
            imgsz_height=imgsz_height,
            fast=fast,
        )
        control.future = future

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
            chunks.append(f"===== {name} =====\n{read_text_tail(path, MAX_LOG_RESPONSE_BYTES)}")
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
    if job.get("status") in ACTIVE_STATUSES:
        raise HTTPException(status_code=409, detail="cannot delete a queued or running job")
    remove_job_dir(job_dir, docker_image=job.get("docker_image", "pulsar2:6.0"))
    return {"deleted": True, "job_id": job_id}


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    job_dir = get_job_dir(job_id)
    job = read_job_json(job_dir)
    if job.get("status") not in ACTIVE_STATUSES:
        raise HTTPException(status_code=409, detail="can only cancel queued or running jobs")

    request_cancel(job_dir)
    with job_controls_lock:
        control = job_controls.get(job_id)
        if control is not None:
            control.cancel_requested = True
            process = control.process
            future = control.future
        else:
            process = None
            future = None

    cancelled_before_start = bool(future and future.cancel())
    if process is not None:
        terminate_process_tree(process)
    cleanup_warning = remove_job_container(job_dir, expect_container=job.get("stage") in {"pulsar2", "tpumlir"})

    job = read_job_json(job_dir)
    job.update({"status": "cancelled", "completed_at": now_iso()})
    if cleanup_warning:
        job["cleanup_warning"] = cleanup_warning
    write_json(job_dir / "job.json", job)
    if cancelled_before_start:
        with job_controls_lock:
            job_controls.pop(job_id, None)
    return {"cancelled": True, "job_id": job_id, "cleanup_warning": cleanup_warning}


@app.websocket("/api/jobs/{job_id}/stream")
async def stream_job(websocket: WebSocket, job_id: str):
    remote_without_token = not API_TOKEN and not is_loopback_client(websocket.client.host if websocket.client else "")
    if remote_without_token or (API_TOKEN and not websocket_has_valid_token(websocket)):
        await websocket.close(code=4401)
        return
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
                        chunk = f.read(LOG_STREAM_CHUNK_CHARS)
                        offsets[name] = f.tell()
                    if chunk:
                        await websocket.send_json({"type": "log", "name": name, "text": chunk})

            if job.get("status") in FINISHED_STATUSES:
                await websocket.send_json({"type": "done", "status": job.get("status")})
                await websocket.close()
                return

            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        return


def run_conversion(
    *,
    job_id: str,
    job_dir: Path,
    model_path: Path,
    dataset_path: Path,
    model_name: str,
    target: str,
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
        "--target",
        target,
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
        try:
            with job_controls_lock:
                control = job_controls.setdefault(job_id, JobControl())
                if control.cancel_requested or is_cancel_requested(job_dir):
                    return
                process = subprocess.Popen(
                    cmd,
                    cwd=BASE_DIR,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    env={
                        **os.environ,
                        "PYTHONIOENCODING": "utf-8",
                        "PYTHONUTF8": "1",
                        "PYTHONUNBUFFERED": "1",
                    },
                    **process_group_options(),
                )
                control.process = process
                (job_dir / "runner.pid").write_text(str(process.pid), encoding="ascii")

            capture_process_output(process, log)
            returncode = process.wait()
            if returncode != 0 and not is_cancel_requested(job_dir):
                ensure_failed_job(job_dir, f"converter exited with code {returncode}")
        except Exception as exc:
            if not is_cancel_requested(job_dir):
                ensure_failed_job(job_dir, f"failed to start or monitor converter: {type(exc).__name__}: {exc}")
        finally:
            (job_dir / "runner.pid").unlink(missing_ok=True)
            with job_controls_lock:
                job_controls.pop(job_id, None)


def process_group_options() -> dict:
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def capture_process_output(process: subprocess.Popen, log) -> None:
    if process.stdout is None:
        return
    written_bytes = 0
    truncated = False
    while True:
        chunk = os.read(process.stdout.fileno(), 64 * 1024)
        if not chunk:
            break
        if truncated:
            continue
        remaining = MAX_API_LOG_BYTES - written_bytes
        if len(chunk) <= remaining:
            log.write(chunk.decode("utf-8", errors="replace"))
            written_bytes += len(chunk)
        else:
            if remaining > 0:
                log.write(chunk[:remaining].decode("utf-8", errors="replace"))
            log.write("\n[api log truncated]\n")
            truncated = True
        log.flush()


def terminate_process_tree(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return

    if os.name == "nt":
        run_taskkill(process.pid, force=False)
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return

    try:
        process.wait(timeout=5)
        return
    except subprocess.TimeoutExpired:
        pass

    if os.name == "nt":
        run_taskkill(process.pid, force=True)
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        return


def run_taskkill(pid: int, *, force: bool) -> None:
    cmd = ["taskkill", "/PID", str(pid), "/T"]
    if force:
        cmd.append("/F")
    try:
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass


def remove_job_container(job_dir: Path, *, expect_container: bool = False) -> str:
    container_name = docker_container_name(job_dir)
    try:
        result = subprocess.run(
            ["docker", "rm", "-f", container_name],
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=10,
            check=False,
        )
    except FileNotFoundError:
        return "docker command not found while cleaning up the task container" if expect_container else ""
    except subprocess.TimeoutExpired:
        return f"timed out while removing Docker container {container_name}" if expect_container else ""

    output = result.stdout.strip()
    if result.returncode == 0 or "No such container" in output:
        return ""
    if not expect_container:
        return ""
    return f"failed to remove Docker container {container_name}: {output or f'exit code {result.returncode}'}"


def save_upload(upload: UploadFile, path: Path, *, max_bytes: int, label: str) -> None:
    total = 0
    with path.open("wb") as f:
        while True:
            chunk = upload.file.read(UPLOAD_CHUNK_BYTES)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"{label} upload exceeds the {max_bytes // (1024 * 1024)} MB limit",
                )
            f.write(chunk)


def read_text_tail(path: Path, max_bytes: int) -> str:
    size = path.stat().st_size
    with path.open("rb") as f:
        if size > max_bytes:
            f.seek(-max_bytes, os.SEEK_END)
            f.readline()
            prefix = "[earlier log output omitted]\n"
        else:
            prefix = ""
        return prefix + f.read().decode("utf-8", errors="replace")


def ensure_job_executor() -> ThreadPoolExecutor:
    global job_executor
    if job_executor is None:
        job_executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_JOBS, thread_name_prefix="conversion")
    return job_executor


def extract_request_token(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return request.headers.get("x-maix-token", "").strip()


def request_has_valid_token(request: Request) -> bool:
    token = request.cookies.get(AUTH_COOKIE_NAME, "") or extract_request_token(request)
    return bool(token) and hmac.compare_digest(token, API_TOKEN)


def is_loopback_client(host: str) -> bool:
    if host in {"localhost", "testclient"}:
        return True
    try:
        return ipaddress.ip_address(host.split("%", 1)[0]).is_loopback
    except ValueError:
        return False


def websocket_has_valid_token(websocket: WebSocket) -> bool:
    token = websocket.cookies.get(AUTH_COOKIE_NAME, "")
    if not token:
        authorization = websocket.headers.get("authorization", "")
        if authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
    return bool(token) and hmac.compare_digest(token, API_TOKEN)


def cancel_all_active_jobs(reason: str) -> None:
    with job_controls_lock:
        controls = list(job_controls.items())

    for job_id, control in controls:
        job_dir = JOBS_DIR / job_id
        try:
            job = read_job_json(job_dir) if job_dir.is_dir() else {}
        except HTTPException:
            job = {}
        if job_dir.is_dir():
            request_cancel(job_dir)
        control.cancel_requested = True
        if control.future is not None:
            control.future.cancel()
        if control.process is not None:
            terminate_process_tree(control.process)
        cleanup_warning = (
            remove_job_container(job_dir, expect_container=job.get("stage") in {"pulsar2", "tpumlir"})
            if job_dir.is_dir()
            else ""
        )
        mark_interrupted_job(job_dir, reason, cleanup_warning=cleanup_warning)

    with job_controls_lock:
        job_controls.clear()


def reconcile_interrupted_jobs() -> None:
    for job_dir in iter_job_dirs():
        try:
            job = read_job_json(job_dir)
        except HTTPException:
            continue
        if job.get("status") not in ACTIVE_STATUSES:
            continue
        request_cancel(job_dir)
        terminate_recorded_process(job_dir, job)
        (job_dir / "runner.pid").unlink(missing_ok=True)
        cleanup_warning = remove_job_container(
            job_dir,
            expect_container=job.get("stage") in {"pulsar2", "tpumlir"},
        )
        mark_interrupted_job(job_dir, "server restarted while the task was active", cleanup_warning=cleanup_warning)


def terminate_recorded_process(job_dir: Path, job: dict) -> None:
    try:
        pid_text = (job_dir / "runner.pid").read_text(encoding="ascii").strip()
    except OSError:
        pid_text = str(job.get("runner_pid", 0))
    try:
        pid = int(pid_text)
    except (TypeError, ValueError):
        return
    if pid <= 1:
        return

    cmdline = read_process_command_line(pid)
    if not cmdline:
        return
    if "convert_cli.py" not in cmdline.lower() or str(job_dir).lower() not in cmdline.lower():
        return

    if os.name == "nt":
        run_taskkill(pid, force=True)
        return

    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    for _ in range(20):
        try:
            os.killpg(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.1)
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def read_process_command_line(pid: int) -> str:
    if os.name == "nt":
        try:
            result = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-Command",
                    f"(Get-CimInstance Win32_Process -Filter 'ProcessId = {pid}').CommandLine",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=10,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return ""
        return result.stdout.strip() if result.returncode == 0 else ""

    cmdline_path = Path(f"/proc/{pid}/cmdline")
    try:
        return cmdline_path.read_bytes().replace(b"\0", b" ").decode("utf-8", errors="replace")
    except OSError:
        return ""


def mark_interrupted_job(job_dir: Path, reason: str, *, cleanup_warning: str = "") -> None:
    if not job_dir.is_dir():
        return
    try:
        job = read_job_json(job_dir)
    except HTTPException:
        return
    if job.get("status") not in ACTIVE_STATUSES:
        return
    job.update({"status": "cancelled", "completed_at": now_iso(), "error": reason})
    if cleanup_warning:
        job["cleanup_warning"] = cleanup_warning
    write_json(job_dir / "job.json", job)


def job_cleanup_loop() -> None:
    run_cleanup_safely("startup")
    while not cleanup_stop_event.wait(JOBS_CLEAN_INTERVAL_SECONDS):
        run_cleanup_safely("scheduled")


def run_cleanup_safely(reason: str) -> None:
    try:
        cleanup_finished_jobs(reason)
    except Exception as exc:
        print(f"[job-cleanup] cleanup failed during {reason}: {type(exc).__name__}: {exc}", file=sys.stderr)


def cleanup_finished_jobs(reason: str) -> dict:
    if JOBS_KEEP_DAYS <= 0 and JOBS_KEEP_COUNT <= 0:
        return {"deleted": [], "failed": [], "reason": reason}
    if not JOBS_DIR.exists():
        return {"deleted": [], "failed": [], "reason": reason}

    candidates = []
    for job_dir in iter_job_dirs():
        try:
            job = read_job_json(job_dir)
        except HTTPException:
            continue
        status = job.get("status")
        if status in ACTIVE_STATUSES or status not in FINISHED_STATUSES:
            continue
        candidates.append(
            {
                "job_dir": job_dir,
                "job": job,
                "time": get_job_sort_time(job_dir, job),
            }
        )

    delete_dirs = set()
    now = datetime.now()
    if JOBS_KEEP_DAYS > 0:
        cutoff = now - timedelta(days=JOBS_KEEP_DAYS)
        delete_dirs.update(item["job_dir"] for item in candidates if item["time"] < cutoff)

    if JOBS_KEEP_COUNT > 0:
        newest_first = sorted(candidates, key=lambda item: item["time"], reverse=True)
        delete_dirs.update(item["job_dir"] for item in newest_first[JOBS_KEEP_COUNT:])

    deleted = []
    failed = []
    for job_dir in sorted(delete_dirs):
        job = next((item["job"] for item in candidates if item["job_dir"] == job_dir), {})
        try:
            remove_job_dir(job_dir, docker_image=job.get("docker_image", "pulsar2:6.0"))
            deleted.append(job_dir.name)
        except Exception as exc:
            failed.append({"job_id": job_dir.name, "error": str(exc)})

    if deleted or failed:
        print(
            "[job-cleanup]",
            json.dumps({"reason": reason, "deleted": deleted, "failed": failed}, ensure_ascii=False),
            file=sys.stderr,
        )
    return {"deleted": deleted, "failed": failed, "reason": reason}


def get_job_sort_time(job_dir: Path, job: dict) -> datetime:
    for key in ["completed_at", "created_at"]:
        value = job.get(key)
        if isinstance(value, str) and value:
            try:
                parsed = datetime.fromisoformat(value)
                if parsed.tzinfo is not None:
                    parsed = parsed.astimezone().replace(tzinfo=None)
                return parsed
            except ValueError:
                pass
    return datetime.fromtimestamp(job_dir.stat().st_mtime)


def remove_job_dir(job_dir: Path, docker_image: str) -> None:
    try:
        rmtree(job_dir)
        return
    except PermissionError:
        if supports_posix_ids():
            repair_job_owner_with_docker(job_dir, docker_image=docker_image)
        else:
            make_tree_writable(job_dir)

    try:
        rmtree(job_dir)
    except PermissionError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"failed to delete job because some files are not writable: {exc}",
        ) from exc


def repair_job_owner_with_docker(job_dir: Path, docker_image: str) -> None:
    if not supports_posix_ids():
        raise HTTPException(
            status_code=500,
            detail="failed to delete job because permission repair with chown is not supported on this platform",
        )
    uid = os.getuid()
    gid = os.getgid()
    cmd = [
        "docker",
        "run",
        "--rm",
        "--mount",
        docker_bind_mount(job_dir, "/data"),
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


def supports_posix_ids() -> bool:
    return hasattr(os, "getuid") and hasattr(os, "getgid")


def make_tree_writable(root: Path) -> None:
    for path in sorted(root.rglob("*"), reverse=True):
        try:
            path.chmod(0o700 if path.is_dir() else 0o600)
        except OSError:
            pass
    try:
        root.chmod(0o700)
    except OSError:
        pass


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
        "target": job.get("target", ""),
        "yolo_version": job.get("yolo_version", ""),
        "labels_num": job.get("labels_num", ""),
        "created_at": job.get("created_at", ""),
        "completed_at": job.get("completed_at", ""),
    }


def read_jobs_list() -> list[dict]:
    jobs = []
    for path in sorted(iter_job_dirs(), reverse=True):
        jobs.append(read_job_summary(path))
    return jobs


def iter_job_dirs() -> list[Path]:
    if not JOBS_DIR.exists():
        return []
    root = JOBS_DIR.resolve()
    job_dirs = []
    for path in JOBS_DIR.iterdir():
        if not path.is_dir() or not JOB_ID_PATTERN.fullmatch(path.name):
            continue
        try:
            if not is_relative_to(path.resolve(), root):
                continue
        except OSError:
            continue
        job_dirs.append(path)
    return job_dirs


def read_job_json(job_dir: Path) -> dict:
    path = job_dir / "job.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="job metadata not found")
    try:
        with path.open("r", encoding="utf-8") as f:
            job = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail=f"invalid job metadata: {exc}") from exc
    job.setdefault("job_id", job_dir.name)
    return job


def get_job_dir(job_id: str) -> Path:
    if not JOB_ID_PATTERN.fullmatch(job_id):
        raise HTTPException(status_code=400, detail="invalid job_id")
    job_dir = JOBS_DIR / job_id
    try:
        if not is_relative_to(job_dir.resolve(), JOBS_DIR.resolve()):
            raise HTTPException(status_code=400, detail="invalid job_id")
    except FileNotFoundError:
        pass
    if not job_dir.is_dir():
        raise HTTPException(status_code=404, detail="job not found")
    return job_dir


def write_json(path: Path, data: dict) -> None:
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}.{threading.get_ident()}")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def new_job_id(model_name: str, target: str, yolo_version: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"{stamp}_{model_name}_{target}_{yolo_version}"


def default_docker_image(target: str) -> str:
    if target == "maixcam2":
        return "pulsar2:6.0"
    if target == "maixcam":
        return "maixcam-tpumlir:v3.4"
    return "pulsar2:6.0"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def slugify(value: str) -> str:
    return sanitize_model_name(value)


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
    if job.get("status") in FINISHED_STATUSES:
        return
    job.update({"status": "failed", "completed_at": now_iso(), "error": error})
    write_json(job_dir / "job.json", job)
