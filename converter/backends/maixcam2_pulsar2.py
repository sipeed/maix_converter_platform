import json
import os
import shlex
import shutil
import subprocess
import tarfile
import textwrap
import time
from pathlib import Path

from converter.yolo.mud import write_maixcam2_yolo_mud
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

    images = sorted(p for p in dataset_dir.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES)
    if len(images) < images_num:
        raise ValueError(f"not enough calibration images: have {len(images)}, need {images_num}")
    for old in images_dir.iterdir():
        if old.is_file():
            old.unlink()
    for index, image in enumerate(images[:images_num]):
        shutil.copy2(image, images_dir / f"{index:06d}_{image.name}")

    write_maixcam2_yolo_mud(
        out_dir / f"{model_name}.mud",
        model_name=model_name,
        model_type=profile.model_type,
        labels=labels,
    )
    write_container_script(job_dir / "convert_inside_docker.py", profile=profile)


def run_pulsar2_job(
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
        "--mount",
        docker_bind_mount(job_dir, "/data"),
        docker_image,
    ]
    fast_arg = " --fast" if fast else ""
    stdin_text = (
        "cd /data\n"
        f"python convert_inside_docker.py --model-name {shlex.quote(model_name)} --images-num {images_num}{fast_arg}\n"
        "status=$?\n"
        f"{host_chown_command()}"
        "exit $status\n"
    )
    run_and_log(cmd, job_dir / "convert.log", stdin_text=stdin_text)


def host_chown_command() -> str:
    if not hasattr(os, "getuid") or not hasattr(os, "getgid"):
        return ""
    return f"chown -R {os.getuid()}:{os.getgid()} /data || true\n"


def docker_bind_mount(host_path: Path, container_path: str) -> str:
    source = host_path.resolve().as_posix()
    if "," in source or "," in container_path:
        raise ValueError(f"Docker bind mount path cannot contain comma: {source} -> {container_path}")
    return f"type=bind,source={source},target={container_path}"


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
        )
        if stdin_text and process.stdin is not None:
            process.stdin.write(stdin_text.encode("utf-8"))
            process.stdin.close()
        assert process.stdout is not None
        for raw_line in process.stdout:
            line = raw_line.decode("utf-8", errors="replace")
            print(line, end="")
            log.write(line)
            log.flush()
        code = process.wait()
        if code != 0:
            error = subprocess.CalledProcessError(code, cmd)
            raise RuntimeError(f"command failed with exit code {code}, see log: {log_path}") from error


def write_container_script(path: Path, profile: YoloProfile) -> None:
    output_nodes = [
        {"name": node.name, "dst_perm": list(node.dst_perm) if node.dst_perm else None}
        for node in profile.output_nodes
    ]
    script = r'''
import argparse
import json
import shutil
import subprocess
import tarfile
from pathlib import Path

import onnx


OUTPUT_NODES = __OUTPUT_NODES__
OUTPUT_NAMES = [node["name"] for node in OUTPUT_NODES]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--images-num", type=int, default=100)
    parser.add_argument("--fast", action="store_true")
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

    build_model("NPU1", "vnpu", sim, config_dir / "__YOLO_VERSION___vnpu.json", out_dir, args.model_name, args.images_num, args.fast)
    build_model("NPU2", "npu", sim, config_dir / "__YOLO_VERSION___npu.json", out_dir, args.model_name, args.images_num, args.fast)
    print("done")
    subprocess.run(["ls", "-lh", str(out_dir)], check=False)


def extract_onnx(input_path: Path, output_path: Path):
    print("Step 1: extract ONNX outputs")
    try:
        onnx.utils.extract_model(str(input_path), str(output_path), ["images"], OUTPUT_NAMES)
    except ValueError:
        model = onnx.load(input_path)
        inferred = onnx.shape_inference.infer_shapes(model)
        inferred_path = output_path.with_suffix(".inferred.onnx")
        onnx.save(inferred, inferred_path)
        onnx.utils.extract_model(str(inferred_path), str(output_path), ["images"], OUTPUT_NAMES)
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


def make_config(npu_mode: str, config_path: Path, images_num: int, fast: bool):
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
            "precision_analysis": not fast,
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
        "output_processors": make_output_processors(),
        "compiler": {
            "check": 0 if fast else 3,
            "check_mode": "CheckOutput",
            "check_cosine_simularity": 0.9,
        },
    }
    with config_path.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    print("saved config:", config_path)


def make_output_processors():
    processors = []
    for node in OUTPUT_NODES:
        processor = {"tensor_name": node["name"]}
        if node.get("dst_perm"):
            processor["dst_perm"] = node["dst_perm"]
        processors.append(processor)
    return processors


def build_model(npu_mode: str, suffix: str, onnx_path: Path, config_path: Path, out_dir: Path, model_name: str, images_num: int, fast: bool):
    print(f"Step 4: build {model_name}_{suffix}.axmodel")
    build_dir = Path("/data/tmp_build")
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)
    make_config(npu_mode, config_path, images_num, fast)
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
    script = script.replace("__OUTPUT_NODES__", repr(output_nodes))
    script = script.replace("__YOLO_VERSION__", profile.yolo_version)
    path.write_text(textwrap.dedent(script).lstrip(), encoding="utf-8", newline="\n")


def new_job_dir(root: Path, model_name: str, profile: YoloProfile) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    return root / f"{stamp}_{model_name}_maixcam2_{profile.yolo_version}"
