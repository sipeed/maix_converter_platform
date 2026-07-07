YOLO26_DETECT_OUTPUTS = [
    "/model.23/one2one_cv2.0/one2one_cv2.0.2/Conv_output_0",
    "/model.23/one2one_cv2.1/one2one_cv2.1.2/Conv_output_0",
    "/model.23/one2one_cv2.2/one2one_cv2.2.2/Conv_output_0",
    "/model.23/one2one_cv3.0/one2one_cv3.0.2/Conv_output_0",
    "/model.23/one2one_cv3.1/one2one_cv3.1.2/Conv_output_0",
    "/model.23/one2one_cv3.2/one2one_cv3.2.2/Conv_output_0",
]


def get_output_nodes(yolo_version: str, task: str) -> list[str]:
    key = (yolo_version.lower(), task.lower())
    if key == ("yolo26", "detect"):
        return YOLO26_DETECT_OUTPUTS
    raise ValueError(f"unsupported yolo/task profile: {yolo_version}/{task}")
