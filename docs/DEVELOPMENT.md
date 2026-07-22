# Maix Converter Platform 开发文档

当前阶段目标：YOLO detect + MaixCam2 + Pulsar2。

支持输入：

- YOLO26 `.onnx`
- YOLO26 `.pt`，会先用 Ultralytics 导出 ONNX，再进入 MaixCam2 转换流程
- YOLO11 `.onnx`
- YOLO11 `.pt`，会先用 Ultralytics 导出 ONNX，再进入 MaixCam2 转换流程
- YOLOv8 `.onnx`
- YOLOv8 `.pt`，会先用 Ultralytics 导出 ONNX，再进入 MaixCam2 转换流程
- 量化图片目录或 `.zip` 压缩包

## 输入目录

模型和量化图片建议放在 `inputs/` 目录，这个目录已经被 git 忽略：

```text
inputs/
  models/
    yolo26n.pt
    yolo11n.pt
    yolov8n.pt
  datasets/
    coco/
      000000000139.jpg
      000000000285.jpg
    coco.zip
```

## 命令行测试

使用 `.onnx` 输入：

```bash
cd maix_converter_platform
python convert_cli.py \
  --model inputs/models/yolo26n.onnx \
  --dataset inputs/datasets/coco \
  --model-name yolo26n \
  --images-num 100
```

默认使用 `--yolo-version yolo26`。转换 YOLO11 时指定 `--yolo-version yolo11`：

```bash
python convert_cli.py \
  --model inputs/models/yolo11n.pt \
  --dataset inputs/datasets/coco \
  --model-name yolo11n \
  --yolo-version yolo11 \
  --imgsz 640 480 \
  --images-num 100
```

转换 YOLOv8 时指定 `--yolo-version yolov8`：

```bash
python convert_cli.py \
  --model inputs/models/yolov8n.pt \
  --dataset inputs/datasets/coco \
  --model-name yolov8n \
  --yolo-version yolov8 \
  --imgsz 640 480 \
  --images-num 100
```

使用 `.pt` 输入时，需要在安装了 `ultralytics` 的 Python 环境中执行，比如你的 conda `yolo` 环境：

```bash
cd maix_converter_platform
python convert_cli.py \
  --model inputs/models/yolo26n.pt \
  --dataset inputs/datasets/coco \
  --model-name yolo26n \
  --yolo-version yolo26 \
  --imgsz 640 480 \
  --images-num 100
```

`--imgsz 640 480` 表示宽 640、高 480，导出的 ONNX 输入形状是 `[1, 3, 480, 640]`。

量化数据集也可以传 zip：

```bash
python convert_cli.py \
  --model inputs/models/yolo26n.pt \
  --dataset inputs/datasets/coco.zip \
  --model-name yolo26n \
  --yolo-version yolo26 \
  --imgsz 640 480 \
  --images-num 100
```

zip 里可以直接放图片，也可以有一层或多层目录，程序会递归查找 `.jpg/.jpeg/.png/.bmp`。

调试转换流程时可以加 `--fast`，会关闭 Pulsar2 精度分析和输出校验，转换会更快：

```bash
python convert_cli.py \
  --model inputs/models/yolo26n.pt \
  --dataset inputs/datasets \
  --model-name yolo26n \
  --yolo-version yolo26 \
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

转换 Ultralytics 导出的 `.pt` 或 `.onnx` 时，程序会优先从模型 metadata 里读取类别名写入 `.mud`。如果没有读取到类别名，才会回退到 COCO 80 类。自训练模型一定要保证 `.mud` 里的 `labels` 数量和模型类别输出数量一致，否则 MaixPy 后处理会按错误类别数解析输出。

## YOLO Profile

当前只接入 MaixCam2 detect 任务：

| YOLO 版本 | MUD `model_type` | 输出节点 |
| --- | --- | --- |
| YOLO26 | `yolo26` | `/model.23/one2one_cv2.0/one2one_cv2.0.2/Conv_output_0`<br>`/model.23/one2one_cv2.1/one2one_cv2.1.2/Conv_output_0`<br>`/model.23/one2one_cv2.2/one2one_cv2.2.2/Conv_output_0`<br>`/model.23/one2one_cv3.0/one2one_cv3.0.2/Conv_output_0`<br>`/model.23/one2one_cv3.1/one2one_cv3.1.2/Conv_output_0`<br>`/model.23/one2one_cv3.2/one2one_cv3.2.2/Conv_output_0` |
| YOLO11 | `yolo11` | `/model.23/dfl/conv/Conv_output_0`<br>`/model.23/Sigmoid_output_0` |
| YOLOv8 | `yolov8` | `/model.22/dfl/conv/Conv_output_0`<br>`/model.22/Sigmoid_output_0` |

YOLO11 这里使用 MaixPy 文档里 MaixCam2 推荐的两个输出节点。不要使用 `/model.23/Concat_output_0`、`/model.23/Concat_1_output_0`、`/model.23/Concat_2_output_0` 这组三输出方案；它在 MaixCam2 上容易量化失败。

后续计划：

- YOLOv5 detect
- MaixCam / MaixCam Pro 后端

## Web API

Web 后端使用 FastAPI。因为 `.pt` 导出依赖 `ultralytics`，建议在你的 conda `yolo` 环境里安装和运行：

```bash
cd maix_converter_platform
conda activate yolo
pip install -r requirements-web.txt
```

启动服务：

```bash
python -m uvicorn web.app:app --host 127.0.0.1 --port 8000
```

该命令可用于 Linux、macOS 和 Windows。需要局域网访问时，请按照 README 设置 `HOST=0.0.0.0` 并使用访问令牌。

浏览器打开：

```text
http://127.0.0.1:8000/
```

页面支持模型上传、数据集上传、上传进度、实时日志、任务状态、任务配置回显、失败错误摘要、结果 zip 下载和任务删除。

## 任务清理策略

Web 服务启动时会启动一个后台清理线程，只扫描 `jobs/` 目录，不扫描也不删除根目录下的 `inputs/`。

默认配置：

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `MAIX_JOBS_AUTO_CLEAN` | `1` | 是否启用自动清理，设为 `0`、`false`、`no` 或 `off` 可关闭 |
| `MAIX_JOBS_KEEP_DAYS` | `7` | 已结束任务超过多少天后可以删除，`0` 表示关闭按时间清理 |
| `MAIX_JOBS_KEEP_COUNT` | `30` | 保留多少个最新的已结束任务，`0` 表示关闭按数量清理 |
| `MAIX_JOBS_CLEAN_INTERVAL_SECONDS` | `21600` | 定时清理间隔，最小值为 60 秒 |

清理规则：

- 只清理状态为 `success` 或 `failed` 的任务
- 跳过 `queued` 和 `running` 任务
- 跳过缺失 `job.json` 或状态未知的目录
- 删除的是整个 `jobs/<job_id>/` 任务目录，因此会一起删除 `uploads/`、`input/`、`export/`、`out/`、日志和 zip
- 删除时复用 `remove_job_dir()`，如果遇到 Docker/root 创建的文件，会先尝试用 Docker 修复 owner 再删除
- 某个任务清理失败不会影响 Web 服务运行，只会写入服务端 stderr

最近任务列表使用 SSE 单向推送，服务端在任务摘要变化时发送新列表：

```text
GET /api/jobs/events
```

单个任务日志使用 WebSocket 增量推送：

```text
WS /api/jobs/{job_id}/stream
```

健康检查：

```bash
curl http://127.0.0.1:8000/api/health
```

创建转换任务：

```bash
curl -X POST http://127.0.0.1:8000/api/jobs \
  -F "model=@inputs/models/yolo26n.pt" \
  -F "dataset=@inputs/datasets.zip" \
  -F "model_name=yolo26n_web_test" \
  -F "yolo_version=yolo26" \
  -F "images_num=100" \
  -F "imgsz_width=640" \
  -F "imgsz_height=480" \
  -F "fast=true"
```

返回里的 `job_id` 用来查询状态：

```bash
curl http://127.0.0.1:8000/api/jobs/<job_id>
curl http://127.0.0.1:8000/api/jobs/<job_id>/log
```

转换完成后下载 zip：

```bash
curl -L -o result.zip http://127.0.0.1:8000/api/jobs/<job_id>/download
```

当前接口：

```text
GET  /api/health
POST /api/jobs
GET  /api/jobs
GET  /api/jobs/events
GET  /api/jobs/{job_id}
GET  /api/jobs/{job_id}/log
GET  /api/jobs/{job_id}/download
DELETE /api/jobs/{job_id}
```
