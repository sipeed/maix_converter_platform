from dataclasses import dataclass


@dataclass(frozen=True)
class OutputNode:
    name: str
    dst_perm: tuple[int, ...] | None = None


@dataclass(frozen=True)
class YoloProfile:
    yolo_version: str
    task: str
    model_type: str
    output_nodes: tuple[OutputNode, ...]

    @property
    def output_names(self) -> list[str]:
        return [node.name for node in self.output_nodes]

    @property
    def mud_type(self) -> str:
        return "detector" if self.task == "detect" else self.task


YOLO26_DETECT_OUTPUTS = [
    OutputNode("/model.23/one2one_cv2.0/one2one_cv2.0.2/Conv_output_0", (0, 2, 3, 1)),
    OutputNode("/model.23/one2one_cv2.1/one2one_cv2.1.2/Conv_output_0", (0, 2, 3, 1)),
    OutputNode("/model.23/one2one_cv2.2/one2one_cv2.2.2/Conv_output_0", (0, 2, 3, 1)),
    OutputNode("/model.23/one2one_cv3.0/one2one_cv3.0.2/Conv_output_0", (0, 2, 3, 1)),
    OutputNode("/model.23/one2one_cv3.1/one2one_cv3.1.2/Conv_output_0", (0, 2, 3, 1)),
    OutputNode("/model.23/one2one_cv3.2/one2one_cv3.2.2/Conv_output_0", (0, 2, 3, 1)),
]

YOLO11_DETECT_OUTPUTS = [
    OutputNode("/model.23/dfl/conv/Conv_output_0"),
    OutputNode("/model.23/Sigmoid_output_0"),
]

YOLOV8_DETECT_OUTPUTS = [
    OutputNode("/model.22/dfl/conv/Conv_output_0"),
    OutputNode("/model.22/Sigmoid_output_0"),
]

YOLO11_SEG_OUTPUTS = [
    OutputNode("/model.23/dfl/conv/Conv_output_0"),
    OutputNode("/model.23/Sigmoid_output_0"),
    OutputNode("/model.23/Concat_2_output_0"),
    OutputNode("output1"),
]

YOLOV8_SEG_OUTPUTS = [
    OutputNode("/model.22/dfl/conv/Conv_output_0"),
    OutputNode("/model.22/Sigmoid_output_0"),
    OutputNode("/model.22/Concat_2_output_0"),
    OutputNode("output1"),
]

YOLO11_OBB_OUTPUTS = [
    OutputNode("/model.23/dfl/conv/Conv_output_0"),
    OutputNode("/model.23/Sigmoid_1_output_0"),
    OutputNode("/model.23/Sigmoid_output_0"),
]

YOLOV8_OBB_OUTPUTS = [
    OutputNode("/model.22/dfl/conv/Conv_output_0"),
    OutputNode("/model.22/Sigmoid_1_output_0"),
    OutputNode("/model.22/Sigmoid_output_0"),
]

PROFILES = {
    ("yolo26", "detect"): YoloProfile(
        yolo_version="yolo26",
        task="detect",
        model_type="yolo26",
        output_nodes=tuple(YOLO26_DETECT_OUTPUTS),
    ),
    ("yolo11", "detect"): YoloProfile(
        yolo_version="yolo11",
        task="detect",
        model_type="yolo11",
        output_nodes=tuple(YOLO11_DETECT_OUTPUTS),
    ),
    ("yolov8", "detect"): YoloProfile(
        yolo_version="yolov8",
        task="detect",
        model_type="yolov8",
        output_nodes=tuple(YOLOV8_DETECT_OUTPUTS),
    ),
    ("yolo11", "seg"): YoloProfile(
        yolo_version="yolo11",
        task="seg",
        model_type="yolo11",
        output_nodes=tuple(YOLO11_SEG_OUTPUTS),
    ),
    ("yolov8", "seg"): YoloProfile(
        yolo_version="yolov8",
        task="seg",
        model_type="yolov8",
        output_nodes=tuple(YOLOV8_SEG_OUTPUTS),
    ),
    ("yolo11", "obb"): YoloProfile(
        yolo_version="yolo11",
        task="obb",
        model_type="yolo11",
        output_nodes=tuple(YOLO11_OBB_OUTPUTS),
    ),
    ("yolov8", "obb"): YoloProfile(
        yolo_version="yolov8",
        task="obb",
        model_type="yolov8",
        output_nodes=tuple(YOLOV8_OBB_OUTPUTS),
    ),
}


def get_yolo_profile(yolo_version: str, task: str) -> YoloProfile:
    key = (yolo_version.lower(), task.lower())
    if key in PROFILES:
        return PROFILES[key]
    raise ValueError(f"unsupported yolo/task profile: {yolo_version}/{task}")


def get_output_nodes(yolo_version: str, task: str) -> list[str]:
    return get_yolo_profile(yolo_version, task).output_names
