import argparse
from pathlib import Path

from converter.backends.maixcam2_pulsar2 import new_job_dir, prepare_job, run_pulsar2_job
from converter.yolo.export import export_pt_to_onnx
from converter.yolo.labels import parse_labels


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp"}


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
    parser.add_argument("--docker-image", default="pulsar2:6.0", help="Pulsar2 docker image")
    parser.add_argument("--jobs-dir", default="jobs", help="job output root directory")
    args = parser.parse_args()

    model_path = Path(args.model).expanduser().resolve()
    dataset_dir = Path(args.dataset).expanduser().resolve()
    model_name = args.model_name.strip() or model_path.stem
    labels = parse_labels(args.labels)
    validate_inputs(model_path, dataset_dir, args.images_num)

    jobs_root = Path(args.jobs_dir).expanduser().resolve()
    job_dir = new_job_dir(jobs_root, model_name)
    print("job:", job_dir)

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
    )
    print("result:", job_dir / "out")
    print("log:", job_dir / "convert.log")


def validate_inputs(model_path: Path, dataset_dir: Path, images_num: int) -> None:
    if not model_path.is_file():
        raise FileNotFoundError(f"model not found: {model_path}")
    if not dataset_dir.is_dir():
        raise FileNotFoundError(f"dataset dir not found: {dataset_dir}")
    images = [p for p in dataset_dir.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES]
    if len(images) < images_num:
        raise ValueError(f"not enough calibration images: have {len(images)}, need {images_num}")


if __name__ == "__main__":
    main()
