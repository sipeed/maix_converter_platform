from pathlib import Path


def write_maixcam2_yolo_mud(
    path: Path,
    *,
    model_name: str,
    model_type: str,
    labels: list[str],
) -> None:
    labels_text = ", ".join(labels)
    text = f"""[basic]
type = axmodel
model_npu = {model_name}_npu.axmodel
model_vnpu = {model_name}_vnpu.axmodel

[extra]
model_type = {model_type}
type=detector
input_type = rgb
labels = {labels_text}

input_cache = true
output_cache = true
input_cache_flush = false
output_cache_inval = true

mean = 0,0,0
scale = 0.00392156862745098, 0.00392156862745098, 0.00392156862745098
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
