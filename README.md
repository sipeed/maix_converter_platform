# Maix Converter Platform

Maix Converter Platform 是一个面向 MaixCam2 的 YOLO 模型转换网页工具。它的目标是把原本需要手动敲很多命令、准备配置文件、进入 Docker、复制结果文件的转换流程，整理成一个更容易使用的 Web 页面。

你只需要上传 YOLO 模型和量化图片数据集，选择 YOLO 版本、输入分辨率和转换参数，平台就会自动完成：

- `.pt` 导出 `.onnx`
- ONNX 输出节点裁剪
- 量化图片打包
- Pulsar2 转换
- 生成 `.mud`
- 生成 MaixCam2 可用的 `.axmodel`
- 打包转换结果 zip

## 当前支持

- 设备：MaixCam2
- 任务：Detect
- YOLO26
- YOLO11
- YOLOv8
- 输入模型：`.pt` / `.onnx`
- 量化数据集：`.zip`

## 1. 克隆项目

```bash
git clone git@github.com:liangzhuohua/maix_converter_platform.git
cd maix_converter_platform
```

如果你使用 HTTPS：

```bash
git clone https://github.com/liangzhuohua/maix_converter_platform.git
cd maix_converter_platform
```

## 2. 准备 Python 环境

建议使用 conda 单独创建一个环境：

```bash
conda create -n maix-converter python=3.11
conda activate maix-converter
```

安装 Web 服务依赖：

```bash
pip install -r requirements-web.txt
```

如果你需要上传 `.pt` 模型，让平台自动导出 ONNX，还需要安装 Ultralytics：

```bash
pip install ultralytics onnx
```

如果你只上传已经导出的 `.onnx`，可以不安装 `ultralytics`。但如果是自训练模型，建议安装 `onnx`，这样平台可以从 ONNX metadata 里读取类别名并写入 `.mud`。

## 3. 安装 Docker

平台使用 Docker 运行 Pulsar2 转换环境。你需要先安装 Docker，并确认当前用户可以执行 `docker`。

Windows 建议安装 Docker Desktop，并启用 WSL2 backend。项目所在磁盘需要能被 Docker Desktop 访问，否则后续转换时可能无法把 `jobs/` 目录挂载进容器。安装完成后打开 PowerShell 或 Anaconda Prompt 检查：

```bash
docker --version
docker ps
```

Linux 用户可以参考下面的 Ubuntu / Debian 命令。

Ubuntu / Debian 可以参考：

```bash
sudo apt update
sudo apt install docker.io
sudo usermod -aG docker $USER
```

执行完 `usermod` 后，需要重新登录终端，或者重启系统。然后检查：

```bash
docker --version
docker ps
```

如果 `docker ps` 没有权限错误，就说明 Docker 基本可用。

## 4. 安装 Pulsar2 Docker 镜像

MaixCam2 模型转换使用的是 AX620E 工具链。按照 [Sipeed MaixCAM2 模型转换文档](https://wiki.sipeed.com/maixpy/doc/zh/ai_model_converter/maixcam2.html)，推荐把 Pulsar2 放在 Docker 里运行，这样可以避免宿主机 Python、系统库和工具链版本不匹配。

本项目默认调用的 Docker 镜像名是：

```text
pulsar2:6.0
```

你需要先获取 Pulsar2 Docker 镜像包。镜像包通常是 `.tar` 或 `.tar.gz` 文件，文件名可能因版本不同而变化。

加载镜像：

```bash
docker load -i <你的_pulsar2_镜像包.tar>
```

如果你的镜像包是 `.tar.gz`，也可以直接加载：

```bash
docker load -i <你的_pulsar2_镜像包.tar.gz>
```

加载完成后查看镜像：

```bash
docker images
```

你需要确认列表里有一个可用的 Pulsar2 镜像。如果镜像名已经是 `pulsar2:6.0`，可以直接进入下一步。

如果加载出来的镜像名不是 `pulsar2:6.0`，需要给它打一个 tag。比如 `docker images` 显示的是：

```text
REPOSITORY   TAG
pulsar2      6.0
```

那就不需要处理。如果显示的是其他名字，比如：

```text
REPOSITORY        TAG
sipeed/pulsar2    latest
```

则执行：

```bash
docker tag sipeed/pulsar2:latest pulsar2:6.0
```

如果显示的是：

```text
REPOSITORY   TAG
pulsar2      3.3
```

则执行：

```bash
docker tag pulsar2:3.3 pulsar2:6.0
```

再次确认：

```bash
docker images | grep pulsar2
```

最后可以简单验证容器里的 Pulsar2 是否可用：

```bash
docker run --rm pulsar2:6.0 -c "pulsar2 version"
```

如果输出类似下面这样，就说明镜像基本可用：

```text
version: 6.0
commit: 48520c11
```

也可以查看 Pulsar2 支持的子命令：

```bash
docker run --rm pulsar2:6.0 -c "pulsar2 --help | head -20"
```

正常会看到类似：

```text
usage: main.py [-h] {version,build,run,llm_build} ...
```

> 平台运行转换任务时会自动调用 Docker，不需要你手动进入容器。只有在排查环境问题时，才需要手动运行上面的验证命令。

## 5. 启动网页端

进入项目目录并激活 Python 环境：

```bash
cd maix_converter_platform
conda activate maix-converter
```

启动服务：

```bash
uvicorn web.app:app --host 0.0.0.0 --port 8000
```

浏览器打开：

```text
http://127.0.0.1:8000/
```

如果你是在另一台电脑访问这台转换服务器，把 `127.0.0.1` 换成服务器 IP。

## 6. 准备上传文件

模型文件支持：

- `.pt`
- `.onnx`

量化数据集必须上传 `.zip` 文件。zip 里面只需要图片，不需要标注文件。

支持图片格式：

- `.jpg`
- `.jpeg`
- `.png`
- `.bmp`

zip 可以直接放图片：

```text
dataset.zip
  000001.jpg
  000002.jpg
  000003.jpg
```

也可以有目录：

```text
dataset.zip
  images/
    000001.jpg
    000002.jpg
```

建议选择和实际使用场景接近的图片。调试时可以先用 50 到 100 张，正式转换可以适当增加。

## 7. 网页选项说明

### 模型文件

上传你要转换的 YOLO 模型。

- 上传 `.pt`：平台会先用 Ultralytics 导出 ONNX，再继续转换
- 上传 `.onnx`：平台直接进入 MaixCam2 转换流程

### 量化数据集

上传图片数据集 zip。它用于量化校准，不需要标签文件。

量化数据集越接近真实摄像头画面，转换后的模型效果通常越稳定。

### 模型名称

输出文件的基础名称。比如填写：

```text
yolo11n
```

输出结果会类似：

```text
yolo11n.mud
yolo11n_npu.axmodel
yolo11n_vnpu.axmodel
```

### YOLO 版本

选择模型对应的 YOLO 类型：

- `YOLO26 Detect`
- `YOLO11 Detect`
- `YOLOv8 Detect`

这个选项会影响输出节点选择和 `.mud` 里的 `model_type`，必须和模型实际版本对应。

### 图片数量

参与量化校准的图片数量。这个数量不能超过 zip 里实际图片数量。

建议：

- 快速测试：`50` 到 `100`
- 正式转换：根据数据集情况增加

### 宽度 / 高度

模型输入分辨率。

例如填写：

```text
宽度 640
高度 480
```

对应输入形状是 `[1, 3, 480, 640]`。宽高必须和你希望在 MaixCam2 上运行的模型输入尺寸一致。

### 快速模式

快速模式会跳过部分 Pulsar2 精度分析和输出校验，转换速度更快，适合调试流程。

正式部署到 MaixCam2 前，建议关闭快速模式重新转换一次。

## 8. 开始转换和下载结果

填写完选项后，点击“开始转换”。

页面会显示：

- 上传进度
- 当前任务状态
- 转换日志
- 最近任务列表
- 下载结果按钮

转换成功后，“下载结果”按钮会变成可点击状态。下载得到的是一个 zip，里面包含：

```text
model_name.mud
model_name_npu.axmodel
model_name_vnpu.axmodel
```

把这几个文件放到 MaixCam2 的同一个目录中，然后在 MaixPy 代码里加载 `.mud`。

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

如果你转换的是其他 YOLO 版本，代码里的模型类需要换成 MaixPy 对应接口。

## 9. 任务目录和自动清理

每次转换都会生成一个任务目录：

```text
jobs/<job_id>/
```

里面包含日志、临时文件、输出结果和结果 zip。

平台默认会自动清理旧任务：

- 只清理 `jobs/<job_id>/`
- 不清理根目录下的 `inputs/`
- 不清理 `queued` 或 `running` 任务
- 已结束任务超过 7 天会被清理
- 已结束任务超过 30 个时，会优先清理更旧的任务
- Web 服务启动时清理一次，之后每 6 小时清理一次

可以用环境变量调整：

```bash
MAIX_JOBS_KEEP_DAYS=7
MAIX_JOBS_KEEP_COUNT=30
MAIX_JOBS_CLEAN_INTERVAL_SECONDS=21600
```

关闭自动清理：

```bash
MAIX_JOBS_AUTO_CLEAN=0
```

## 常见问题

### 为什么需要量化数据集？

MaixCam2 使用 NPU 量化模型。转换工具需要用一批图片统计模型中间层的数据范围，然后把浮点模型转换成适合 NPU 运行的量化模型。

### `.pt` 和 `.onnx` 应该上传哪个？

如果你只有训练后的 `.pt`，可以直接上传 `.pt`。

如果你已经有确认可用的 `.onnx`，上传 `.onnx` 会更直接。

### 自训练模型类别数不对怎么办？

平台会优先从 Ultralytics `.pt` 或 `.onnx` metadata 里读取类别名，并写入 `.mud`。

如果 MaixCam2 运行时报 `get tensor idx error`，或者模型信息里的 `labels num` 和你的训练类别数不一致，优先检查导出的模型 metadata 和 `.mud` 里的 `labels`。

### 转换失败怎么办？

先看网页里的实时日志。每个任务目录里也会保留：

```text
api.log
convert.log
job.json
```

这些文件可以帮助定位是上传、ONNX 导出、输出节点、量化数据集还是 Pulsar2 转换阶段出错。

## 开发文档

转换节点、Web API、任务目录结构和后续开发计划放在：

```text
docs/DEVELOPMENT.md
```
