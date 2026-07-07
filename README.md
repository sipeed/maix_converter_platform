# Maix Converter Platform

当前第一阶段目标：YOLO26 detect + MaixCam2 + Pulsar2。

## 命令行测试

在宿主机执行：

```bash
cd /home/ziyue/maixcam2_model/maix_converter_platform
python convert_cli.py \
  --model /home/ziyue/maixcam2_model/maixcam2_yolo26/yolo26n.onnx \
  --dataset /home/ziyue/maixcam2_model/maixcam2_yolo26/coco \
  --model-name yolo26n \
  --images-num 100
```

输出目录会在 `jobs/` 下，每次转换一个独立任务目录。

结果文件：

```text
out/yolo26n.mud
out/yolo26n_npu.axmodel
out/yolo26n_vnpu.axmodel
```
