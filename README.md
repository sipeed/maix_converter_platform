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

调试转换流程时可以加 `--fast`，会关闭 Pulsar2 精度分析和输出校验，转换会更快：

```bash
python convert_cli.py \
  --model inputs/models/yolo26n.pt \
  --dataset inputs/datasets \
  --model-name yolo26n \
  --imgsz 640 480 \
  --images-num 100 \
  --fast
```

最终要放到 MaixCam2 上使用的模型，建议去掉 `--fast` 重新完整转换一次。

输出目录会在 `jobs/` 下，每次转换一个独立任务目录。

结果文件示例：

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

`job.json` 会记录本次转换参数、状态、输出目录、日志路径和 zip 路径。转换失败时也会写入 `status: failed` 和错误信息。

`yolo26n_maixcam2_yolo26.zip` 可以直接解压后复制到 MaixCam2。
