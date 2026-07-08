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


YOLO26_DETECT_OUTPUTS = [
    OutputNode("/model.23/one2one_cv2.0/one2one_cv2.0.2/Conv_output_0", (0, 2, 3, 1)),
    OutputNode("/model.23/one2one_cv2.1/one2one_cv2.1.2/Conv_output_0", (0, 2, 3, 1)),
    OutputNode("/model.23/one2one_cv2.2/one2one_cv2.2.2/Conv_output_0", (0, 2, 3, 1)),
    OutputNode("/model.23/one2one_cv3.0/one2one_cv3.0.2/Conv_output_0", (0, 2, 3, 1)),
    OutputNode("/model.23/one2one_cv3.1/one2one_cv3.1.2/Conv_output_0", (0, 2, 3, 1)),
    OutputNode("/model.23/one2one_cv3.2/one2one_cv3.2.2/Conv_output_0", (0, 2, 3, 1)),
]

YOLO11_DETECT_OUTPUTS = [
    OutputNode("/model.23/dfl/conv/Conv_output_0", (0, 2, 3, 1)),
    OutputNode("/model.23/Sigmoid_output_0"),
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
}


def get_yolo_profile(yolo_version: str, task: str) -> YoloProfile:
    key = (yolo_version.lower(), task.lower())
    if key in PROFILES:
        return PROFILES[key]
    raise ValueError(f"unsupported yolo/task profile: {yolo_version}/{task}")


def get_output_nodes(yolo_version: str, task: str) -> list[str]:
    return get_yolo_profile(yolo_version, task).output_names
