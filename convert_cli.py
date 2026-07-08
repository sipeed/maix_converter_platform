import argparse
import json
import os
import re
import zipfile
from datetime import datetime
from pathlib import Path

from converter.backends.maixcam2_pulsar2 import new_job_dir, prepare_job, run_pulsar2_job
from converter.yolo.export import export_pt_to_onnx
from converter.yolo.labels import parse_labels
from converter.yolo.node_profiles import get_yolo_profile


def main():
    parser = argparse.ArgumentParser(description="Convert YOLO detect model to MaixCam2 axmodel.")
    parser.add_argument("--model", required=True, help="YOLO .pt or .onnx model path")
    parser.add_argument("--dataset", required=True, help="calibration image directory or .zip file")
    parser.add_argument("--model-name", default="", help="output model base name, default is model stem")
    parser.add_argument("--labels", default="", help="comma separated labels, default is COCO labels")
    parser.add_argument("--yolo-version", default="yolo26", choices=["yolo11", "yolo26"], help="YOLO profile")
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
        help="skip Pulsar2 precision analysis and output checks for faster debug builds",
    )
    parser.add_argument("--docker-image", default="pulsar2:6.0", help="Pulsar2 docker image")
    parser.add_argument("--jobs-dir", default="jobs", help="job output root directory")
    parser.add_argument("--job-dir", default="", help="exact job directory, mainly used by the web API")
    args = parser.parse_args()

    model_path = Path(args.model).expanduser().resolve()
    dataset_path = Path(args.dataset).expanduser().resolve()
    model_name = clean_model_name(args.model_name.strip() or model_path.stem)
    labels = parse_labels(args.labels)
    profile = get_yolo_profile(args.yolo_version, args.task)

    if args.images_num < 1:
        raise ValueError("--images-num must be >= 1")
    width, height = args.imgsz
    validate_imgsz(width, height)

    if args.job_dir:
        job_dir = Path(args.job_dir).expanduser().resolve()
    else:
        jobs_root = Path(args.jobs_dir).expanduser().resolve()
        job_dir = new_job_dir(jobs_root, model_name, profile=profile)
    job_dir.mkdir(parents=True, exist_ok=True)
    print("job:", job_dir)

    metadata = {
        "status": "running",
        "created_at": now_iso(),
        "model_name": model_name,
        "yolo_version": profile.yolo_version,
        "task": profile.task,
        "input_model": str(model_path),
        "input_suffix": model_path.suffix.lower(),
        "dataset": str(dataset_path),
        "dataset_suffix": dataset_path.suffix.lower(),
        "labels_num": len(labels),
        "images_num": args.images_num,
        "imgsz": args.imgsz,
        "opset": args.opset,
        "simplify_onnx": args.simplify_onnx,
        "fast": args.fast,
        "docker_image": args.docker_image,
        "output_dir": str(job_dir / "out"),
        "log": str(job_dir / "convert.log"),
    }
    write_job_json(job_dir, metadata)

    try:
        dataset_dir = prepare_dataset_path(dataset_path, job_dir)
        metadata["prepared_dataset"] = str(dataset_dir)
        write_job_json(job_dir, metadata)

        suffix = model_path.suffix.lower()
        if suffix == ".pt":
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
            write_job_json(job_dir, metadata)
        elif suffix != ".onnx":
            raise ValueError(f"unsupported model suffix: {model_path.suffix}, expected .pt or .onnx")

        prepare_job(
            job_dir=job_dir,
            model_path=model_path,
            dataset_dir=dataset_dir,
            model_name=model_name,
            profile=profile,
            labels=labels,
            images_num=args.images_num,
        )
        run_pulsar2_job(
            job_dir=job_dir,
            model_name=model_name,
            docker_image=args.docker_image,
            images_num=args.images_num,
            fast=args.fast,
        )
        zip_path = package_outputs(job_dir, model_name, profile=profile)
        metadata.update(
            {
                "status": "success",
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


def package_outputs(job_dir: Path, model_name: str, profile) -> Path:
    out_dir = job_dir / "out"
    files = sorted(p for p in out_dir.iterdir() if p.is_file())
    if not files:
        raise FileNotFoundError(f"no output files found in {out_dir}")

    zip_path = job_dir / f"{model_name}_maixcam2_{profile.yolo_version}.zip"
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
        extract_zip_safely(dataset_path, dst)
        return dst
    raise FileNotFoundError(f"dataset must be an image directory or .zip file: {dataset_path}")


def extract_zip_safely(zip_path: Path, dst_dir: Path) -> None:
    dst_root = dst_dir.resolve()
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            target = (dst_dir / info.filename).resolve()
            if dst_root not in [target, *target.parents]:
                raise ValueError(f"unsafe zip entry: {info.filename}")
            zf.extract(info, dst_dir)


def write_job_json(job_dir: Path, metadata: dict) -> None:
    path = job_dir / "job.json"
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def clean_model_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("._-")
    if not cleaned:
        raise ValueError("--model-name cannot be empty")
    return cleaned[:80]


def validate_imgsz(width: int, height: int) -> None:
    for name, value in [("width", width), ("height", height)]:
        if value < 32 or value > 4096:
            raise ValueError(f"--imgsz {name} must be between 32 and 4096")
        if value % 32 != 0:
            raise ValueError(f"--imgsz {name} must be a multiple of 32")


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


if __name__ == "__main__":
    main()
