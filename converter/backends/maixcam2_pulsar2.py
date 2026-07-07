import json
import shutil
import subprocess
import tarfile
import textwrap
import time
from pathlib import Path

from converter.yolo.mud import write_maixcam2_yolo_mud
from converter.yolo.node_profiles import get_output_nodes


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp"}


def prepare_job(
    *,
    job_dir: Path,
    model_path: Path,
    dataset_dir: Path,
    model_name: str,
    labels: list[str],
    images_num: int,
) -> None:
    if not model_path.is_file():
        raise FileNotFoundError(f"model not found: {model_path}")
    if model_path.suffix.lower() != ".onnx":
        raise ValueError("MVP currently supports ONNX input only")
    if not dataset_dir.is_dir():
        raise FileNotFoundError(f"dataset dir not found: {dataset_dir}")

    job_dir.mkdir(parents=True, exist_ok=True)
    input_dir = job_dir / "input"
    images_dir = job_dir / "coco"
    out_dir = job_dir / "out"
    for path in [input_dir, images_dir, out_dir]:
        path.mkdir(parents=True, exist_ok=True)

    shutil.copy2(model_path, job_dir / f"{model_name}.onnx")

    images = sorted(p for p in dataset_dir.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)
    if len(images) < images_num:
        raise ValueError(f"not enough calibration images: have {len(images)}, need {images_num}")
    for old in images_dir.iterdir():
        if old.is_file():
            old.unlink()
    for image in images[:images_num]:
        shutil.copy2(image, images_dir / image.name)

    write_maixcam2_yolo_mud(
        out_dir / f"{model_name}.mud",
        model_name=model_name,
        model_type="yolo26",
        labels=labels,
    )
    write_container_script(job_dir / "convert_inside_docker.py")


def run_pulsar2_job(
    *,
    job_dir: Path,
    model_name: str,
    docker_image: str,
    images_num: int,
) -> None:
    cmd = [
        "docker",
        "run",
        "-i",
        "--rm",
        "-v",
        f"{job_dir.resolve()}:/data",
        docker_image,
    ]
    stdin_text = (
        "cd /data\n"
        f"python convert_inside_docker.py --model-name {model_name} --images-num {images_num}\n"
        "exit\n"
    )
    run_and_log(cmd, job_dir / "convert.log", stdin_text=stdin_text)


def run_and_log(cmd: list[str], log_path: Path, stdin_text: str | None = None) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        log.write("+ " + " ".join(cmd) + "\n")
        if stdin_text:
            log.write(stdin_text)
        log.flush()
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE if stdin_text else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        if stdin_text and process.stdin is not None:
            process.stdin.write(stdin_text)
            process.stdin.close()
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="")
            log.write(line)
            log.flush()
        code = process.wait()
        if code != 0:
            raise subprocess.CalledProcessError(code, cmd)


def write_container_script(path: Path) -> None:
    script = r'''
import argparse
import json
import shutil
import subprocess
import tarfile
from pathlib import Path

import onnx


OUTPUT_NODES = [
    "/model.23/one2one_cv2.0/one2one_cv2.0.2/Conv_output_0",
    "/model.23/one2one_cv2.1/one2one_cv2.1.2/Conv_output_0",
    "/model.23/one2one_cv2.2/one2one_cv2.2.2/Conv_output_0",
    "/model.23/one2one_cv3.0/one2one_cv3.0.2/Conv_output_0",
    "/model.23/one2one_cv3.1/one2one_cv3.1.2/Conv_output_0",
    "/model.23/one2one_cv3.2/one2one_cv3.2.2/Conv_output_0",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--images-num", type=int, default=100)
    args = parser.parse_args()

    model_path = Path(f"/data/{args.model_name}.onnx")
    images_dir = Path("/data/coco")
    if not model_path.exists():
        raise SystemExit(f"model not found: {model_path}")
    if not images_dir.is_dir():
        raise SystemExit(f"calibration image dir not found: {images_dir}")

    tmp1 = Path("/data/tmp1")
    tmp_build = Path("/data/tmp_build")
    tmp_images = Path("/data/tmp_images")
    config_dir = Path("/data/config")
    out_dir = Path("/data/out")

    for path in [tmp1, tmp_build, tmp_images, config_dir]:
        if path.exists():
            shutil.rmtree(path)
    for path in [tmp1, tmp_images, config_dir, out_dir]:
        path.mkdir(parents=True, exist_ok=True)

    extracted = tmp1 / f"{args.model_name}_extracted.onnx"
    sim = tmp1 / f"{args.model_name}_sim.onnx"
    extract_onnx(model_path, extracted)
    simplify_or_copy(extracted, sim)
    pack_images(images_dir, args.images_num, tmp_images / "images.tar")

    build_model("NPU1", "vnpu", sim, config_dir / "yolo26_vnpu.json", out_dir, args.model_name, args.images_num)
    build_model("NPU2", "npu", sim, config_dir / "yolo26_npu.json", out_dir, args.model_name, args.images_num)
    print("done")
    subprocess.run(["ls", "-lh", str(out_dir)], check=False)


def extract_onnx(input_path: Path, output_path: Path):
    print("Step 1: extract ONNX outputs")
    try:
        onnx.utils.extract_model(str(input_path), str(output_path), ["images"], OUTPUT_NODES)
    except ValueError:
        model = onnx.load(input_path)
        inferred = onnx.shape_inference.infer_shapes(model)
        inferred_path = output_path.with_suffix(".inferred.onnx")
        onnx.save(inferred, inferred_path)
        onnx.utils.extract_model(str(inferred_path), str(output_path), ["images"], OUTPUT_NODES)
    print("saved:", output_path)


def simplify_or_copy(input_path: Path, output_path: Path):
    print("Step 2: simplify ONNX")
    if shutil.which("onnxsim"):
        subprocess.run(["onnxsim", str(input_path), str(output_path)], check=True)
    else:
        print("onnxsim not found, copy extracted ONNX")
        shutil.copy2(input_path, output_path)
    print("saved:", output_path)


def pack_images(images_dir: Path, images_num: int, tar_path: Path):
    print("Step 3: generate calibration image tar")
    work_dir = tar_path.parent / "images"
    images = sorted(p for p in images_dir.iterdir() if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".bmp"])
    if len(images) < images_num:
        raise SystemExit(f"not enough images: have {len(images)}, need {images_num}")
    work_dir.mkdir(parents=True, exist_ok=True)
    for src in images[:images_num]:
        shutil.copy2(src, work_dir / src.name)
    with tarfile.open(tar_path, "w") as tar:
        for image in sorted(work_dir.iterdir()):
            tar.add(image, arcname=image.name)
    print("saved:", tar_path)


def make_config(npu_mode: str, config_path: Path, images_num: int):
    config = {
        "model_type": "ONNX",
        "npu_mode": npu_mode,
        "quant": {
            "input_configs": [
                {
                    "tensor_name": "images",
                    "calibration_dataset": "/data/tmp_images/images.tar",
                    "calibration_format": "Image",
                    "calibration_size": images_num,
                    "calibration_mean": [0, 0, 0],
                    "calibration_std": [255, 255, 255],
                }
            ],
            "calibration_method": "MinMax",
            "precision_analysis": True,
        },
        "input_processors": [
            {
                "tensor_name": "images",
                "tensor_format": "RGB",
                "tensor_layout": "NCHW",
                "src_format": "RGB",
                "src_dtype": "U8",
                "src_layout": "NHWC",
                "csc_mode": "NoCSC",
            }
        ],
        "output_processors": [
            {
                "tensor_name": name,
                "dst_perm": [0, 2, 3, 1],
            }
            for name in OUTPUT_NODES
        ],
        "compiler": {
            "check": 3,
            "check_mode": "CheckOutput",
            "check_cosine_simularity": 0.9,
        },
    }
    with config_path.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    print("saved config:", config_path)


def build_model(npu_mode: str, suffix: str, onnx_path: Path, config_path: Path, out_dir: Path, model_name: str, images_num: int):
    print(f"Step 4: build {model_name}_{suffix}.axmodel")
    build_dir = Path("/data/tmp_build")
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)
    make_config(npu_mode, config_path, images_num)
    subprocess.run(
        [
            "pulsar2",
            "build",
            "--target_hardware",
            "AX620E",
            "--input",
            str(onnx_path),
            "--output_dir",
            str(build_dir),
            "--config",
            str(config_path),
        ],
        check=True,
    )
    compiled = build_dir / "compiled.axmodel"
    if not compiled.exists():
        raise SystemExit(f"compiled model missing: {compiled}")
    dst = out_dir / f"{model_name}_{suffix}.axmodel"
    shutil.copy2(compiled, dst)
    print("saved:", dst)


if __name__ == "__main__":
    main()
'''
    path.write_text(textwrap.dedent(script).lstrip(), encoding="utf-8")


def new_job_dir(root: Path, model_name: str) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    return root / f"{stamp}_{model_name}_maixcam2_yolo26"
