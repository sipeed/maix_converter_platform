# Maix Converter Platform

Maix Converter Platform 是一个面向 MaixCam2 的 YOLO 模型转换工具。你可以在网页里上传模型和量化图片数据集，选择 YOLO 版本和输入分辨率，然后自动生成 MaixPy 可用的 `.mud`、`.axmodel` 和结果压缩包。

当前支持：

- MaixCam2
- YOLO26 Detect
- YOLO11 Detect
- YOLOv8 Detect
- `.pt` 模型输入
- `.onnx` 模型输入
- `.zip` 量化图片数据集输入

## 准备环境

你需要提前准备好：

- Python 环境，建议使用已经安装 `ultralytics` 的 conda `yolo` 环境
- Docker
- Pulsar2 Docker 镜像：`pulsar2:6.0`

如果要转换 `.pt` 模型，需要 Python 环境里可以正常导入 `ultralytics`。如果只转换 `.onnx`，不需要执行 `.pt` 导出步骤，但 Web 服务仍建议在同一个环境里运行。

安装 Web 服务依赖：

```bash
cd /home/ziyue/maixcam2_model/maix_converter_platform
conda activate yolo
pip install -r requirements-web.txt
```

## 启动网页

```bash
cd /home/ziyue/maixcam2_model/maix_converter_platform
conda activate yolo
uvicorn web.app:app --host 0.0.0.0 --port 8000
```

浏览器打开：

```text
http://127.0.0.1:8000/
```

## 准备输入文件

模型文件支持：

- `.pt`
- `.onnx`

量化数据集需要上传 `.zip` 文件。zip 里面可以直接放图片，也可以有多层目录，程序会递归查找图片。

支持的图片格式：

- `.jpg`
- `.jpeg`
- `.png`
- `.bmp`

建议目录结构：

```text
inputs/
  models/
    yolo26n.pt
    yolo11n.pt
    yolov8n.pt
  datasets/
    coco.zip
```

量化图片不需要标注文件，只需要准备一批和实际使用场景接近的图片。一般先用 100 张左右测试流程，正式转换可以根据模型情况增加数量。

## 创建转换任务

在网页里依次填写：

- 模型文件：选择 `.pt` 或 `.onnx`
- 量化数据集：选择 `.zip`
- 模型名称：用于生成输出文件名，比如 `yolo26n`
- YOLO 版本：选择 `YOLO26 Detect`、`YOLO11 Detect` 或 `YOLOv8 Detect`
- 图片数量：参与量化的图片数量
- 分辨率：模型输入宽高，比如 `640 x 480`
- 快速模式：调试时可以打开，正式使用建议关闭后重新转换一次

点击“开始转换”后，页面会显示上传进度、任务状态和实时日志。转换成功后，“下载结果”按钮会变成可点击状态。

## 输出结果

每次转换都会在 `jobs/` 下生成一个独立任务目录，并自动打包 zip。

结果示例：

```text
jobs/20260708_120000_yolo26n_maixcam2_yolo26/
  job.json
  convert.log
  yolo26n_maixcam2_yolo26.zip
  out/
    yolo26n.mud
    yolo26n_npu.axmodel
    yolo26n_vnpu.axmodel
```

网页里的“下载结果”下载的是 zip 文件。解压后会得到：

- `.mud`
- `_npu.axmodel`
- `_vnpu.axmodel`

把这些文件复制到 MaixCam2 上同一个目录里，然后在 MaixPy 代码中加载 `.mud`。

下面以 YOLO11 为例：

```python
from maix import camera, display, image, nn, app

detector = nn.YOLO11(model="/root/yolo11/yolo11n.mud", dual_buff=True)

cam = camera.Camera(detector.input_width(), detector.input_height(), detector.input_format())
disp = display.Display()

while not app.need_exit():
    img = cam.read()
    objs = detector.detect(img, conf_th=0.5, iou_th=0.45)
    for obj in objs:
        img.draw_rect(obj.x, obj.y, obj.w, obj.h, color=image.COLOR_RED)
        msg = f"{detector.labels[obj.class_id]}: {obj.score:.2f}"
        img.draw_string(obj.x, obj.y, msg, color=image.COLOR_RED)
    disp.show(img)
```

如果你转换的是其他 YOLO 版本，代码里的模型类需要换成 MaixPy 对应接口，`.mud`、`_npu.axmodel` 和 `_vnpu.axmodel` 仍然放在同一个目录。

## 常见问题

### 为什么需要量化数据集？

MaixCam2 使用的是 NPU 量化模型。转换工具需要用一批图片统计模型中间层的数据范围，然后把浮点模型转换成适合 NPU 运行的量化模型。图片越接近真实使用场景，量化后的效果通常越稳定。

### `.pt` 和 `.onnx` 应该选哪个？

如果你只有训练后的 `.pt`，可以直接上传 `.pt`，平台会先导出 ONNX 再转换。

如果你已经有确认可用的 `.onnx`，可以直接上传 `.onnx`，这样会跳过 `.pt -> .onnx` 导出步骤。

### 自训练模型类别数不对怎么办？

平台会优先从 Ultralytics `.pt` 或 `.onnx` metadata 里读取类别名，并写入 `.mud`。如果模型 metadata 缺失类别信息，可能会回退到默认类别。

如果 MaixCam2 运行时报 `get tensor idx error`，或者模型信息里的 `labels num` 和你的训练类别数不一致，优先检查导出的模型 metadata 和 `.mud` 里的 `labels`。

### 快速模式可以一直开着吗？

快速模式适合调试流程，会跳过部分 Pulsar2 精度分析和输出校验，转换速度更快。

正式部署到 MaixCam2 前，建议关闭快速模式重新转换一次。

## 命令行转换

除了网页，也可以直接使用命令行：

```bash
python convert_cli.py \
  --model inputs/models/yolo26n.pt \
  --dataset inputs/datasets/coco.zip \
  --model-name yolo26n \
  --yolo-version yolo26 \
  --imgsz 640 480 \
  --images-num 100
```

YOLO11：

```bash
python convert_cli.py \
  --model inputs/models/yolo11n.pt \
  --dataset inputs/datasets/coco.zip \
  --model-name yolo11n \
  --yolo-version yolo11 \
  --imgsz 640 480 \
  --images-num 100
```

YOLOv8：

```bash
python convert_cli.py \
  --model inputs/models/yolov8n.pt \
  --dataset inputs/datasets/coco.zip \
  --model-name yolov8n \
  --yolo-version yolov8 \
  --imgsz 640 480 \
  --images-num 100
```

## 开发文档

转换节点、Web API、任务目录结构和后续开发计划放在：

```text
docs/DEVELOPMENT.md
```
