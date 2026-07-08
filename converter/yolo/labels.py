import ast
from pathlib import Path


COCO_LABELS = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck",
    "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
    "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra",
    "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
    "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
    "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
    "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
    "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear",
    "hair drier", "toothbrush",
]


def parse_labels(value: str | None) -> list[str]:
    if not value:
        raise ValueError("labels cannot be empty")
    labels = [item.strip() for item in value.split(",") if item.strip()]
    if not labels:
        raise ValueError("labels cannot be empty")
    return labels


def resolve_labels(model_path: Path, labels_arg: str | None) -> tuple[list[str], str]:
    if labels_arg:
        return parse_labels(labels_arg), "argument"

    inferred = infer_labels_from_model(model_path)
    if inferred:
        return inferred, "model"

    return COCO_LABELS, "coco"


def infer_labels_from_model(model_path: Path) -> list[str] | None:
    suffix = model_path.suffix.lower()
    if suffix == ".pt":
        return infer_labels_from_pt(model_path)
    if suffix == ".onnx":
        return infer_labels_from_onnx(model_path)
    return None


def infer_labels_from_pt(model_path: Path) -> list[str] | None:
    try:
        from ultralytics import YOLO
    except ImportError:
        return None

    model = YOLO(str(model_path))
    return normalize_names(model.names)


def infer_labels_from_onnx(model_path: Path) -> list[str] | None:
    try:
        import onnx
    except ImportError:
        return None

    model = onnx.load(model_path)
    metadata = {item.key: item.value for item in model.metadata_props}
    return normalize_names_text(metadata.get("names", ""))


def normalize_names_text(value: str) -> list[str] | None:
    if not value:
        return None
    try:
        names = ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return None
    return normalize_names(names)


def normalize_names(names) -> list[str] | None:
    if isinstance(names, dict):
        items = sorted(names.items(), key=lambda item: int(item[0]))
        labels = [str(value).strip() for _, value in items]
    elif isinstance(names, (list, tuple)):
        labels = [str(value).strip() for value in names]
    else:
        return None

    labels = [label for label in labels if label]
    return labels or None
