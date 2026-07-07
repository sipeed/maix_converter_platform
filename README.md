# Maix Converter Platform

当前第一阶段目标：YOLO26 detect + MaixCam2 + Pulsar2。

支持输入：

- YOLO26 `.onnx`
- YOLO26 `.pt`，会先用 Ultralytics 导出 ONNX，再进入 MaixCam2 转换流程

## 输入目录

模型和量化图片建议放在 `inputs/` 目录，这个目录已经被 git 忽略：

```text
inputs/
  models/
    yolo26n.pt
  datasets/
    coco/
      000000000139.jpg
      000000000285.jpg
```

## 命令行测试

使用 `.onnx` 输入：

```bash
cd /home/ziyue/maixcam2_model/maix_converter_platform
python convert_cli.py \
  --model /home/ziyue/maixcam2_model/maixcam2_yolo26/yolo26n.onnx \
  --dataset /home/ziyue/maixcam2_model/maixcam2_yolo26/coco \
  --model-name yolo26n \
  --images-num 100
```

使用 `.pt` 输入时，需要在安装了 `ultralytics` 的 Python 环境中执行，比如你的 conda `yolo` 环境：

```bash
cd /home/ziyue/maixcam2_model/maix_converter_platform
python convert_cli.py \
  --model inputs/models/yolo26n.pt \
  --dataset inputs/datasets/coco \
  --model-name yolo26n \
  --imgsz 640 480 \
  --images-num 100
```

`--imgsz 640 480` 表示宽 640、高 480，导出的 ONNX 输入形状是 `[1, 3, 480, 640]`。

输出目录会在 `jobs/` 下，每次转换一个独立任务目录。

结果文件：

```text
out/yolo26n.mud
out/yolo26n_npu.axmodel
out/yolo26n_vnpu.axmodel
```
