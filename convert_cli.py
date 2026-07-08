import argparse
import json
import zipfile
from datetime import datetime
from pathlib import Path

from converter.backends.maixcam2_pulsar2 import new_job_dir, prepare_job, run_pulsar2_job
from converter.yolo.export import export_pt_to_onnx
from converter.yolo.labels import parse_labels


def main():
    parser = argparse.ArgumentParser(description="Convert YOLO26 detect model to MaixCam2 axmodel.")
    parser.add_argument("--model", required=True, help="YOLO26 .pt or .onnx model path")
    parser.add_argument("--dataset", required=True, help="calibration image directory")
    parser.add_argument("--model-name", default="", help="output model base name, default is model stem")
    parser.add_argument("--labels", default="", help="comma separated labels, default is COCO labels")
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
    args = parser.parse_args()

    model_path = Path(args.model).expanduser().resolve()
    dataset_dir = Path(args.dataset).expanduser().resolve()
    model_name = args.model_name.strip() or model_path.stem
    labels = parse_labels(args.labels)

    jobs_root = Path(args.jobs_dir).expanduser().resolve()
    job_dir = new_job_dir(jobs_root, model_name)
    job_dir.mkdir(parents=True, exist_ok=True)
    print("job:", job_dir)

    metadata = {
        "status": "running",
        "created_at": now_iso(),
        "model_name": model_name,
        "input_model": str(model_path),
        "input_suffix": model_path.suffix.lower(),
        "dataset": str(dataset_dir),
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
        suffix = model_path.suffix.lower()
        if suffix == ".pt":
            width, height = args.imgsz
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
        zip_path = package_outputs(job_dir, model_name)
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


def package_outputs(job_dir: Path, model_name: str) -> Path:
    out_dir = job_dir / "out"
    files = sorted(p for p in out_dir.iterdir() if p.is_file())
    if not files:
        raise FileNotFoundError(f"no output files found in {out_dir}")

    zip_path = job_dir / f"{model_name}_maixcam2_yolo26.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            zf.write(path, arcname=path.name)
    return zip_path


def write_job_json(job_dir: Path, metadata: dict) -> None:
    path = job_dir / "job.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
        f.write("\n")


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


if __name__ == "__main__":
    main()
