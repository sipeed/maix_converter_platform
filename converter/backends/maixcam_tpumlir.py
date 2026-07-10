import os
import shlex
import shutil
import textwrap
import time
from pathlib import Path

from converter.backends.maixcam2_pulsar2 import docker_bind_mount
from converter.backends.process_log import run_and_log
from converter.common.job_control import docker_container_name
from converter.yolo.mud import write_maixcam_yolo_mud
from converter.yolo.node_profiles import YoloProfile


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp"}


def prepare_job(
    *,
    job_dir: Path,
    model_path: Path,
    dataset_dir: Path,
    model_name: str,
    profile: YoloProfile,
    labels: list[str],
    images_num: int,
    input_shape: tuple[int, int],
) -> None:
    if not model_path.is_file():
        raise FileNotFoundError(f"model not found: {model_path}")
    if model_path.suffix.lower() != ".onnx":
        raise ValueError("MaixCAM conversion requires ONNX input")
    if not dataset_dir.is_dir():
        raise FileNotFoundError(f"dataset dir not found: {dataset_dir}")

    job_dir.mkdir(parents=True, exist_ok=True)
    images_dir = job_dir / "coco"
    out_dir = job_dir / "out"
    for path in [images_dir, out_dir]:
        path.mkdir(parents=True, exist_ok=True)

    shutil.copy2(model_path, job_dir / f"{model_name}.onnx")

    images = sorted(p for p in dataset_dir.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES)
    if len(images) < images_num:
        raise ValueError(f"not enough calibration images: have {len(images)}, need {images_num}")
    for old in images_dir.iterdir():
        if old.is_file():
            old.unlink()
    for index, image in enumerate(images[:images_num]):
        shutil.copy2(image, images_dir / f"{index:06d}_{image.name}")
    shutil.copy2(images[0], job_dir / "test_input.jpg")

    write_maixcam_yolo_mud(
        out_dir / f"{model_name}.mud",
        model_name=model_name,
        model_type=profile.model_type,
        labels=labels,
    )
    write_container_script(job_dir / "convert_inside_docker.py", profile=profile, input_shape=input_shape)


def run_tpumlir_job(
    *,
    job_dir: Path,
    model_name: str,
    docker_image: str,
    images_num: int,
    fast: bool = False,
) -> None:
    cmd = [
        "docker",
        "run",
        "-i",
        "--rm",
        "--name",
        docker_container_name(job_dir),
        "--mount",
        docker_bind_mount(job_dir, "/workspace"),
        "-w",
        "/workspace",
        docker_image,
    ]
    fast_arg = " --fast" if fast else ""
    stdin_text = (
        f"python3 convert_inside_docker.py --model-name {shlex.quote(model_name)} --images-num {images_num}{fast_arg}\n"
        "status=$?\n"
        f"{host_chown_command()}"
        "exit $status\n"
    )
    run_and_log(cmd, job_dir / "convert.log", stdin_text=stdin_text)


def host_chown_command() -> str:
    if not hasattr(os, "getuid") or not hasattr(os, "getgid"):
        return ""
    return f"chown -R {os.getuid()}:{os.getgid()} /workspace || true\n"


def write_container_script(path: Path, profile: YoloProfile, input_shape: tuple[int, int]) -> None:
    input_h, input_w = input_shape
    output_names = profile.output_names
    script = r'''
import argparse
import shutil
import subprocess
from pathlib import Path


OUTPUT_NAMES = __OUTPUT_NAMES__
INPUT_H = __INPUT_H__
INPUT_W = __INPUT_W__


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--images-num", type=int, default=100)
    parser.add_argument("--fast", action="store_true")
    args = parser.parse_args()

    model_path = Path(f"{args.model_name}.onnx")
    images_dir = Path("coco")
    out_dir = Path("out")
    if not model_path.exists():
        raise SystemExit(f"model not found: {model_path}")
    if not images_dir.is_dir():
        raise SystemExit(f"calibration image dir not found: {images_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    mlir_path = Path(f"{args.model_name}.mlir")
    cali_table = Path(f"{args.model_name}_cali_table")
    top_outputs = Path(f"{args.model_name}_top_outputs.npz")
    cvimodel = out_dir / f"{args.model_name}.cvimodel"
    test_image = Path("test_input.jpg")

    print("Step 1: transform ONNX to MLIR")
    transform_cmd = [
        "model_transform.py",
        "--model_name",
        args.model_name,
        "--model_def",
        str(model_path),
        "--input_shapes",
        f"[[1,3,{INPUT_H},{INPUT_W}]]",
        "--mean",
        "0,0,0",
        "--scale",
        "0.00392156862745098,0.00392156862745098,0.00392156862745098",
        "--keep_aspect_ratio",
        "--pixel_format",
        "rgb",
        "--channel_format",
        "nchw",
        "--output_names",
        ",".join(OUTPUT_NAMES),
        "--mlir",
        str(mlir_path),
    ]
    if not args.fast:
        transform_cmd.extend(
            [
                "--test_input",
                str(test_image),
                "--test_result",
                str(top_outputs),
                "--tolerance",
                "0.99,0.99",
            ]
        )
    run(transform_cmd)

    print("Step 2: calibrate INT8 table")
    run(
        [
            "run_calibration.py",
            str(mlir_path),
            "--dataset",
            str(images_dir),
            "--input_num",
            str(args.images_num),
            "-o",
            str(cali_table),
        ]
    )

    print("Step 3: deploy INT8 cvimodel")
    deploy_cmd = [
        "model_deploy.py",
        "--mlir",
        str(mlir_path),
        "--quantize",
        "INT8",
        "--quant_input",
        "--calibration_table",
        str(cali_table),
        "--processor",
        "cv181x",
        "--model",
        str(cvimodel),
    ]
    if not args.fast:
        deploy_cmd.extend(
            [
                "--test_input",
                f"{args.model_name}_in_f32.npz",
                "--test_reference",
                str(top_outputs),
                "--tolerance",
                "0.9,0.6",
            ]
        )
    run(deploy_cmd)

    if not cvimodel.exists():
        raise SystemExit(f"cvimodel missing: {cvimodel}")
    print("saved:", cvimodel)
    print("done")
    subprocess.run(["ls", "-lh", str(out_dir)], check=False)


def run(cmd):
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
'''
    script = script.replace("__OUTPUT_NAMES__", repr(output_names))
    script = script.replace("__INPUT_H__", str(input_h))
    script = script.replace("__INPUT_W__", str(input_w))
    path.write_text(textwrap.dedent(script).lstrip(), encoding="utf-8", newline="\n")


def new_job_dir(root: Path, model_name: str, profile: YoloProfile) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    return root / f"{stamp}_{model_name}_maixcam_{profile.yolo_version}"
