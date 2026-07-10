import argparse
import json
import os
import re
import stat
import tempfile
import threading
import zipfile
from datetime import datetime
from pathlib import Path

from converter.backends import maixcam2_pulsar2, maixcam_tpumlir
from converter.common.job_control import docker_container_name, is_cancel_requested
from converter.common.names import sanitize_model_name
from converter.yolo.export import export_pt_to_onnx
from converter.yolo.labels import resolve_labels
from converter.yolo.node_profiles import get_yolo_profile


PROJECT_DIR = Path(__file__).resolve().parent
ZIP_COPY_CHUNK_BYTES = 1024 * 1024


def read_env_int(name: str, default: int, min_value: int = 1) -> int:
    value = os.getenv(name, "")
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return max(min_value, parsed)


MAX_ZIP_ENTRIES = read_env_int("MAIX_MAX_ZIP_ENTRIES", 20000)
MAX_ZIP_UNCOMPRESSED_BYTES = read_env_int("MAIX_MAX_ZIP_UNCOMPRESSED_MB", 12288) * 1024 * 1024
MAX_ZIP_FILE_BYTES = read_env_int("MAIX_MAX_ZIP_FILE_MB", 1024) * 1024 * 1024
MAX_ZIP_COMPRESSION_RATIO = read_env_int("MAIX_MAX_ZIP_COMPRESSION_RATIO", 200)


def main():
    parser = argparse.ArgumentParser(description="Convert YOLO detect model to MaixCAM / MaixCAM2 model package.")
    parser.add_argument("--model", required=True, help="YOLO .pt or .onnx model path")
    parser.add_argument("--dataset", required=True, help="calibration image directory or .zip file")
    parser.add_argument("--target", default="maixcam2", choices=["maixcam2", "maixcam"], help="target device")
    parser.add_argument("--model-name", default="", help="output model base name, default is model stem")
    parser.add_argument("--labels", default="", help="comma separated labels, default is read from model metadata")
    parser.add_argument("--yolo-version", default="yolo26", choices=["yolo11", "yolo26", "yolov8"], help="YOLO profile")
    parser.add_argument("--task", default="detect", choices=["detect"], help="model task")
    parser.add_argument("--images-num", type=int, default=100, help="number of calibration images")
    parser.add_argument(
        "--imgsz",
        type=int,
        nargs=2,
        metavar=("WIDTH", "HEIGHT"),
        default=[640, 480],
        help="export input size for .pt models, default: 640 480",
    )
    parser.add_argument("--opset", type=int, default=17, help="ONNX opset for .pt export")
    parser.add_argument(
        "--simplify-onnx",
        action="store_true",
        help="ask Ultralytics to simplify ONNX when exporting .pt",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="skip expensive output checks for faster debug builds",
    )
    parser.add_argument("--docker-image", default="", help="conversion docker image, default depends on target")
    parser.add_argument("--jobs-dir", default=str(PROJECT_DIR / "jobs"), help="job output root directory")
    parser.add_argument("--job-dir", default="", help="exact job directory, mainly used by the web API")
    args = parser.parse_args()

    model_path = Path(args.model).expanduser().resolve()
    dataset_path = Path(args.dataset).expanduser().resolve()
    model_name = clean_model_name(args.model_name.strip() or model_path.stem)
    profile = get_yolo_profile(args.yolo_version, args.task)
    target = args.target.lower()
    docker_image = args.docker_image or default_docker_image(target)
    warn_yolo_version_mismatch(model_name, profile.yolo_version)

    if args.images_num < 1:
        raise ValueError("--images-num must be >= 1")
    width, height = args.imgsz
    validate_imgsz(width, height)

    if args.job_dir:
        job_dir = Path(args.job_dir).expanduser().resolve()
    else:
        jobs_root = Path(args.jobs_dir).expanduser().resolve()
        job_dir = new_job_dir(jobs_root, model_name, profile=profile, target=target)
    job_dir.mkdir(parents=True, exist_ok=True)
    print("job:", job_dir)
    configure_runtime_directories(job_dir)
    if model_path.suffix.lower() == ".pt":
        configure_safe_pt_loading()
    labels, labels_source = resolve_labels(model_path, args.labels)

    try:
        existing_metadata = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        existing_metadata = {}

    metadata = {
        "status": "running",
        "created_at": existing_metadata.get("created_at", now_iso()),
        "started_at": now_iso(),
        "job_id": existing_metadata.get("job_id", job_dir.name),
        "model_name": model_name,
        "target": target,
        "yolo_version": profile.yolo_version,
        "task": profile.task,
        "input_model": str(model_path),
        "input_suffix": model_path.suffix.lower(),
        "dataset": str(dataset_path),
        "dataset_suffix": dataset_path.suffix.lower(),
        "labels_num": len(labels),
        "labels_source": labels_source,
        "images_num": args.images_num,
        "imgsz": args.imgsz,
        "opset": args.opset,
        "simplify_onnx": args.simplify_onnx,
        "fast": args.fast,
        "docker_image": docker_image,
        "runner_pid": os.getpid(),
        "output_dir": str(job_dir / "out"),
        "log": str(job_dir / "convert.log"),
    }
    try:
        ensure_not_cancelled(job_dir)
        metadata["docker_container"] = docker_container_name(job_dir)
        write_job_json(job_dir, metadata)

        ensure_not_cancelled(job_dir)
        dataset_dir = prepare_dataset_path(dataset_path, job_dir)
        metadata["prepared_dataset"] = str(dataset_dir)
        metadata["stage"] = "prepare_done"
        write_job_json(job_dir, metadata)

        suffix = model_path.suffix.lower()
        if suffix == ".pt":
            ensure_not_cancelled(job_dir)
            metadata["stage"] = "exporting"
            write_job_json(job_dir, metadata)
            model_path = export_pt_to_onnx(
                pt_path=model_path,
                job_dir=job_dir,
                model_name=model_name,
                width=width,
                height=height,
                opset=args.opset,
                simplify=args.simplify_onnx,
            )
            metadata["exported_onnx"] = str(model_path)
            metadata["stage"] = "export_done"
            metadata["imgsz"] = [width, height]
            write_job_json(job_dir, metadata)
        elif suffix != ".onnx":
            raise ValueError(f"unsupported model suffix: {model_path.suffix}, expected .pt or .onnx")

        input_shape = read_onnx_input_hw(model_path, fallback=(height, width))
        metadata["requested_imgsz"] = [width, height]
        metadata["imgsz"] = [input_shape[1], input_shape[0]]
        metadata["onnx_input_shape"] = [1, 3, input_shape[0], input_shape[1]]
        write_job_json(job_dir, metadata)

        ensure_not_cancelled(job_dir)
        metadata["stage"] = "prebuilding"
        write_job_json(job_dir, metadata)
        if target == "maixcam2":
            maixcam2_pulsar2.prepare_job(
                job_dir=job_dir,
                model_path=model_path,
                dataset_dir=dataset_dir,
                model_name=model_name,
                profile=profile,
                labels=labels,
                images_num=args.images_num,
            )
            metadata["stage"] = "prebuild_done"
            write_job_json(job_dir, metadata)

            metadata["stage"] = "pulsar2"
            write_job_json(job_dir, metadata)
            ensure_not_cancelled(job_dir)
            maixcam2_pulsar2.run_pulsar2_job(
                job_dir=job_dir,
                model_name=model_name,
                docker_image=docker_image,
                images_num=args.images_num,
                fast=args.fast,
            )
            metadata["stage"] = "pulsar2_done"
            write_job_json(job_dir, metadata)
        elif target == "maixcam":
            maixcam_tpumlir.prepare_job(
                job_dir=job_dir,
                model_path=model_path,
                dataset_dir=dataset_dir,
                model_name=model_name,
                profile=profile,
                labels=labels,
                images_num=args.images_num,
                input_shape=input_shape,
            )
            metadata["stage"] = "prebuild_done"
            write_job_json(job_dir, metadata)

            metadata["stage"] = "tpumlir"
            write_job_json(job_dir, metadata)
            ensure_not_cancelled(job_dir)
            maixcam_tpumlir.run_tpumlir_job(
                job_dir=job_dir,
                model_name=model_name,
                docker_image=docker_image,
                images_num=args.images_num,
                fast=args.fast,
            )
            metadata["stage"] = "tpumlir_done"
            write_job_json(job_dir, metadata)
        else:
            raise ValueError(f"unsupported target: {target}")

        ensure_not_cancelled(job_dir)
        metadata["stage"] = "packaging"
        write_job_json(job_dir, metadata)
        zip_path = package_outputs(job_dir, model_name, profile=profile, target=target)
        metadata.update(
            {
                "status": "success",
                "stage": "done",
                "completed_at": now_iso(),
                "zip": str(zip_path),
            }
        )
        write_job_json(job_dir, metadata)
        print("result:", job_dir / "out")
        print("zip:", zip_path)
        print("job metadata:", job_dir / "job.json")
        print("log:", job_dir / "convert.log")
    except Exception as exc:
        if isinstance(exc, JobCancelled) or is_cancel_requested(job_dir):
            metadata.update(
                {
                    "status": "cancelled",
                    "completed_at": now_iso(),
                }
            )
            write_job_json(job_dir, metadata)
            print("job cancelled:", job_dir)
            return
        metadata.update(
            {
                "status": "failed",
                "completed_at": now_iso(),
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
        write_job_json(job_dir, metadata)
        print("job metadata:", job_dir / "job.json")
        print("log:", job_dir / "convert.log")
        raise


def package_outputs(job_dir: Path, model_name: str, profile, target: str) -> Path:
    out_dir = job_dir / "out"
    files = sorted(p for p in out_dir.iterdir() if p.is_file())
    if not files:
        raise FileNotFoundError(f"no output files found in {out_dir}")

    zip_path = job_dir / f"{model_name}_{target}_{profile.yolo_version}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            zf.write(path, arcname=path.name)
    return zip_path


def prepare_dataset_path(dataset_path: Path, job_dir: Path) -> Path:
    if dataset_path.is_dir():
        return dataset_path
    if dataset_path.is_file() and dataset_path.suffix.lower() == ".zip":
        dst = job_dir / "dataset"
        dst.mkdir(parents=True, exist_ok=True)
        extract_zip_safely(dataset_path, dst, job_dir=job_dir)
        return dst
    raise FileNotFoundError(f"dataset must be an image directory or .zip file: {dataset_path}")


def default_docker_image(target: str) -> str:
    if target == "maixcam2":
        return "pulsar2:6.0"
    if target == "maixcam":
        return "maixcam-tpumlir:v3.4"
    raise ValueError(f"unsupported target: {target}")


def warn_yolo_version_mismatch(model_name: str, yolo_version: str) -> None:
    lowered = model_name.lower()
    hints = {
        "yolo11": "yolo11",
        "yolov8": "yolov8",
        "yolo8": "yolov8",
        "yolo26": "yolo26",
    }
    for token, expected in hints.items():
        if token in lowered and expected != yolo_version:
            print(
                "WARNING: model name looks like "
                f"{expected}, but --yolo-version is {yolo_version}. "
                "Please choose the YOLO version that matches the model."
            )
            return


def configure_runtime_directories(job_dir: Path) -> None:
    runtime_dir = job_dir / "runtime"
    paths = {
        "YOLO_CONFIG_DIR": runtime_dir / "ultralytics",
        "TORCH_HOME": runtime_dir / "torch",
        "MPLCONFIGDIR": runtime_dir / "matplotlib",
        "XDG_CACHE_HOME": runtime_dir / "cache",
        "HF_HOME": runtime_dir / "huggingface",
        "TMP": runtime_dir / "tmp",
        "TEMP": runtime_dir / "tmp",
        "TMPDIR": runtime_dir / "tmp",
    }
    for name, path in paths.items():
        path.mkdir(parents=True, exist_ok=True)
        os.environ[name] = str(path)
    tempfile.tempdir = str(paths["TMP"])


def configure_safe_pt_loading() -> None:
    if os.getenv("MAIX_ALLOW_UNSAFE_PT", "").lower() in {"1", "true", "yes", "on"}:
        return
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("PyTorch is required to load .pt models") from exc
    match = re.match(r"(\d+)\.(\d+)", torch.__version__)
    if not match or tuple(map(int, match.groups())) < (2, 5):
        raise RuntimeError(
            "secure .pt loading requires torch>=2.5; upgrade PyTorch or upload a trusted ONNX model instead"
        )
    os.environ["ULTRALYTICS_SAFE_LOAD"] = "1"


def new_job_dir(root: Path, model_name: str, profile, target: str) -> Path:
    if target == "maixcam2":
        return maixcam2_pulsar2.new_job_dir(root, model_name, profile=profile)
    if target == "maixcam":
        return maixcam_tpumlir.new_job_dir(root, model_name, profile=profile)
    raise ValueError(f"unsupported target: {target}")


def read_onnx_input_hw(model_path: Path, fallback: tuple[int, int]) -> tuple[int, int]:
    try:
        import onnx
    except ModuleNotFoundError:
        print(
            "onnx package not found on host, use --imgsz as MaixCAM input shape: "
            f"[1, 3, {fallback[0]}, {fallback[1]}]"
        )
        return fallback

    model = onnx.load(model_path)
    if not model.graph.input:
        raise ValueError(f"ONNX model has no inputs: {model_path}")
    input_info = model.graph.input[0]
    dims = []
    for dim in input_info.type.tensor_type.shape.dim:
        if not dim.HasField("dim_value"):
            raise ValueError(f"ONNX input shape must be static for MaixCAM: {input_info.name}")
        dims.append(dim.dim_value)
    if len(dims) != 4:
        raise ValueError(f"ONNX input must be NCHW rank 4 for MaixCAM, got: {dims}")
    if dims[1] != 3:
        raise ValueError(f"ONNX input must have 3 channels in NCHW layout, got: {dims}")
    return dims[2], dims[3]


def extract_zip_safely(zip_path: Path, dst_dir: Path, *, job_dir: Path | None = None) -> None:
    dst_root = dst_dir.resolve()
    with zipfile.ZipFile(zip_path) as zf:
        entries = zf.infolist()
        if len(entries) > MAX_ZIP_ENTRIES:
            raise ValueError(f"zip contains too many entries: {len(entries)} > {MAX_ZIP_ENTRIES}")

        declared_total = 0
        for info in entries:
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ValueError(f"zip symlink entries are not allowed: {info.filename}")
            if info.file_size > MAX_ZIP_FILE_BYTES:
                raise ValueError(f"zip entry is too large: {info.filename}")
            declared_total += info.file_size
            if declared_total > MAX_ZIP_UNCOMPRESSED_BYTES:
                raise ValueError("zip uncompressed size exceeds the configured limit")
            if info.file_size and info.compress_size == 0:
                raise ValueError(f"invalid compressed size for zip entry: {info.filename}")
            if info.compress_size and info.file_size / info.compress_size > MAX_ZIP_COMPRESSION_RATIO:
                raise ValueError(f"zip entry compression ratio is too high: {info.filename}")

        extracted_total = 0
        for info in entries:
            if job_dir is not None:
                ensure_not_cancelled(job_dir)
            target = (dst_dir / info.filename).resolve()
            if dst_root not in [target, *target.parents]:
                raise ValueError(f"unsafe zip entry: {info.filename}")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, target.open("wb") as dst:
                file_total = 0
                while True:
                    chunk = src.read(ZIP_COPY_CHUNK_BYTES)
                    if not chunk:
                        break
                    file_total += len(chunk)
                    extracted_total += len(chunk)
                    if file_total > MAX_ZIP_FILE_BYTES or extracted_total > MAX_ZIP_UNCOMPRESSED_BYTES:
                        raise ValueError("zip extraction exceeds the configured size limit")
                    if job_dir is not None:
                        ensure_not_cancelled(job_dir)
                    dst.write(chunk)


def write_job_json(job_dir: Path, metadata: dict) -> None:
    path = job_dir / "job.json"
    if is_cancel_requested(job_dir):
        if metadata.get("status") != "cancelled":
            return
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}
        if existing.get("status") == "cancelled":
            return
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}.{threading.get_ident()}")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def clean_model_name(value: str) -> str:
    cleaned = sanitize_model_name(value)
    if not cleaned:
        raise ValueError("--model-name cannot be empty")
    return cleaned


def validate_imgsz(width: int, height: int) -> None:
    for name, value in [("width", width), ("height", height)]:
        if value < 32 or value > 4096:
            raise ValueError(f"--imgsz {name} must be between 32 and 4096")
        if value % 32 != 0:
            raise ValueError(f"--imgsz {name} must be a multiple of 32")


class JobCancelled(RuntimeError):
    pass


def ensure_not_cancelled(job_dir: Path) -> None:
    if is_cancel_requested(job_dir):
        raise JobCancelled(f"job was cancelled: {job_dir.name}")


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


if __name__ == "__main__":
    main()
