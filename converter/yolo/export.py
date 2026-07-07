import shutil
from pathlib import Path


def export_pt_to_onnx(
    *,
    pt_path: Path,
    job_dir: Path,
    model_name: str,
    width: int,
    height: int,
    opset: int,
    simplify: bool,
) -> Path:
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise RuntimeError(
            "ultralytics is required for .pt export. "
            "Please run this command in your conda yolo environment."
        ) from exc

    input_dir = job_dir / "input"
    export_dir = job_dir / "export"
    input_dir.mkdir(parents=True, exist_ok=True)
    export_dir.mkdir(parents=True, exist_ok=True)

    local_pt = input_dir / f"{model_name}.pt"
    shutil.copy2(pt_path, local_pt)

    print("export pt to onnx:")
    print("  pt:", local_pt)
    print("  imgsz:", f"{width}x{height}")

    model = YOLO(str(local_pt))
    exported = model.export(
        format="onnx",
        imgsz=[height, width],
        opset=opset,
        simplify=simplify,
        dynamic=False,
        batch=1,
    )

    exported_path = Path(exported)
    if not exported_path.is_file():
        fallback = local_pt.with_suffix(".onnx")
        if fallback.is_file():
            exported_path = fallback
        else:
            raise FileNotFoundError(f"exported ONNX not found: {exported}")

    dst = export_dir / f"{model_name}.onnx"
    shutil.copy2(exported_path, dst)
    print("saved exported onnx:", dst)
    return dst
