# Maix Converter Platform

Maix Converter Platform 是一个面向 MaixCAM / MaixCAM Pro / MaixCam2 的 YOLO 模型转换网页工具。它的目标是把原本需要手动敲很多命令、准备配置文件、进入 Docker、复制结果文件的转换流程，整理成一个更容易使用的 Web 页面。

你只需要上传 YOLO 模型和量化图片数据集，选择 YOLO 版本、输入分辨率和转换参数，平台就会自动完成：

- `.pt` 导出 `.onnx`
- ONNX 输出节点裁剪
- 量化图片打包
- Pulsar2 / TPU-MLIR 转换
- 生成 `.mud`
- 生成 MaixCam2 可用的 `.axmodel`，或 MaixCAM / MaixCAM Pro 可用的 `.cvimodel`
- 打包转换结果 zip

## 当前支持

- 设备：MaixCam2、MaixCAM / MaixCAM Pro
- 任务：Detect
- YOLO26
- YOLO11
- YOLOv8
- 输入模型：`.pt` / `.onnx`
- 量化数据集：`.zip`
- 网页界面：中文

## 1. 克隆项目

```bash
git clone git@github.com:sipeed/maix_converter_platform.git
cd maix_converter_platform
```

如果你使用 HTTPS：

```bash
git clone https://github.com/sipeed/maix_converter_platform.git
cd maix_converter_platform
```

## 2. 准备 Python 环境

如果你使用 conda，建议创建一个专用环境：

```bash
conda create -n maix-converter python=3.11
conda activate maix-converter
```

如果你更喜欢使用 `venv`，也可以这样创建：

Linux / macOS：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Windows CMD：

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate.bat
```

安装 Web 服务依赖：

```bash
pip install -r requirements-web.txt
```

安装模型解析和 `.pt -> .onnx` 转换依赖：

```bash
pip install -r requirements-converter.txt
```

依赖文件固定了已经验证的 Ultralytics 和 ONNX 版本。`.pt` 默认使用受限的安全加载模式，并要求 PyTorch 2.5 或更新版本。仍然建议只上传来源可信的模型；如果只使用 `.onnx`，可以只安装 `requirements-converter.txt` 中的 `onnx`。只有在确认模型绝对可信且必须兼容旧格式时，才可以临时设置 `MAIX_ALLOW_UNSAFE_PT=1`，该选项会恢复不受限的 PyTorch 反序列化。

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

Windows 下如果 Docker 转换阶段报错，优先查看任务目录里的 `convert.log`。如果日志显示路径挂载失败，建议把项目放到你自己的工作区目录中，并使用纯英文短路径，避免中文目录、特殊符号或过深路径影响 Docker bind mount。

接下来请根据目标设备，按照第 4 节或第 5 节手动部署对应的转换镜像。手动部署过程更容易确认镜像来源、版本和每一步执行结果，因此是本文推荐的主要方式。

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
docker images --filter "reference=pulsar2:*"
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
docker run --rm pulsar2:6.0 -c "pulsar2 --help"
```

正常会看到类似：

```text
usage: main.py [-h] {version,build,run,llm_build} ...
```

> 平台运行转换任务时会自动调用 Docker，不需要你手动进入容器。只有在排查环境问题时，才需要手动运行上面的验证命令。

## 5. 安装 MaixCAM / MaixCAM Pro TPU-MLIR Docker 镜像

如果你只转换 MaixCam2，可以跳过本节。

MaixCAM / MaixCAM Pro 使用算能 TPU-MLIR 工具链，底层需要 `model_transform.py`、`run_calibration.py`、`model_deploy.py` 这些命令。官方推荐在 Docker 里使用 TPU-MLIR，避免宿主机 Python、系统库和工具链版本不匹配。

本项目分两层镜像：

```text
sophgo/tpuc_dev:v3.4       # 算能基础开发镜像
maixcam-tpumlir:v3.4       # 本项目使用的镜像，基于上面镜像预装 tpu_mlir
```

平台运行 MaixCAM / MaixCAM Pro 转换时，默认调用的是：

```text
maixcam-tpumlir:v3.4
```

所以你需要先准备 `sophgo/tpuc_dev` 基础镜像，再构建一次 `maixcam-tpumlir:v3.4`。

### 5.1 获取 sophgo/tpuc_dev 基础镜像

先尝试直接拉取：

```bash
docker pull sophgo/tpuc_dev:latest
```

如果能成功，查看镜像：

```bash
docker images --filter "reference=sophgo/tpuc_dev:*"
```

正常会看到类似：

```text
sophgo/tpuc_dev   latest   ...
```

如果 `docker pull` 下载失败，可以参考 [MaixPy MaixCAM 模型转换文档](https://wiki.sipeed.com/maixpy/doc/zh/ai_model_converter/maixcam.html) 和 [TPU-MLIR 官方 README](https://github.com/sophgo/tpu-mlir/blob/master/README_cn.md) 的方式，下载镜像包后导入。

TPU-MLIR 官方 README 当前给出的 v3.4 镜像包地址如下。可以直接使用浏览器下载，或者使用对应平台的命令。

Linux / macOS / WSL：

```bash
curl -L -o tpuc_dev_v3.4.tar.gz https://sophon-assets.sophon.cn/sophon-prod-s3/drive/25/04/15/16/tpuc_dev_v3.4.tar.gz
docker load -i tpuc_dev_v3.4.tar.gz
```

Windows PowerShell / CMD：

```powershell
curl.exe -L -o tpuc_dev_v3.4.tar.gz https://sophon-assets.sophon.cn/sophon-prod-s3/drive/25/04/15/16/tpuc_dev_v3.4.tar.gz
docker load -i tpuc_dev_v3.4.tar.gz
```

本项目建议优先使用 v3.4。导入完成后再次检查：

```bash
docker images --filter "reference=sophgo/tpuc_dev:*"
```

如果看到 `sophgo/tpuc_dev`，就说明基础镜像已经有了。镜像 tag 可能是 `latest`，也可能是 `v3.4`，下一步构建时按实际情况选择命令。

镜像包导入成功后，下载的 `.tar.gz` 文件可以删除，Docker 已经把镜像保存到本地镜像库里。

### 5.2 构建本项目使用的 maixcam-tpumlir 镜像

不要进入 `sophgo/tpuc_dev` 容器后手动执行 `pip install tpu_mlir` 来作为长期方案。`docker run --rm` 启动的是临时容器，退出后容器会被删除，刚刚安装的 Python 包也会消失。

正确做法是构建一次本项目提供的派生镜像，把 `tpu_mlir` 固化到镜像里。

如果你的基础镜像是 `sophgo/tpuc_dev:v3.4`，在项目根目录执行：

```bash
docker build -f docker/maixcam-tpumlir.Dockerfile -t maixcam-tpumlir:v3.4 .
```

如果你的基础镜像只有 `sophgo/tpuc_dev:latest`，执行：

```bash
docker build --build-arg TPUC_DEV_IMAGE=sophgo/tpuc_dev:latest -f docker/maixcam-tpumlir.Dockerfile -t maixcam-tpumlir:v3.4 .
```

构建完成后检查：

```bash
docker images --filter "reference=maixcam-tpumlir:*"
```

正常会看到类似：

```text
maixcam-tpumlir   v3.4   ...
```

### 5.3 验证 TPU-MLIR 命令是否可用

执行：

```bash
docker run --rm maixcam-tpumlir:v3.4 model_transform.py --help
```

正常会看到 `model_transform.py` 的帮助信息，开头类似：

```text
usage: model_transform.py ...
```

再检查部署命令：

```bash
docker run --rm maixcam-tpumlir:v3.4 model_deploy.py --help
```

如果也能看到帮助信息，就代表 MaixCAM / MaixCAM Pro 转换环境可用。

### 5.4 常见问题

如果构建时报：

```text
pull access denied for sophgo/tpuc_dev
```

说明本地没有 `sophgo/tpuc_dev:v3.4`，而 Docker 也没能从网络拉到这个 tag。先用 `docker images --filter "reference=sophgo/tpuc_dev:*"` 看你本地实际的 tag。如果只有 `latest`，使用上面带 `--build-arg TPUC_DEV_IMAGE=sophgo/tpuc_dev:latest` 的构建命令。

如果验证时报：

```text
model_transform.py: command not found
```

说明你运行的不是 `maixcam-tpumlir:v3.4`，或者派生镜像没有构建成功。重新执行 `docker build ... -t maixcam-tpumlir:v3.4 .` 后再验证。

如果下载镜像包很慢，建议先手动用浏览器下载到本机，再执行 `docker load -i <镜像包文件名>`。`docker load` 成功后，原始 `.tar.gz` 镜像包可以删除。

之后平台会默认使用 `maixcam-tpumlir:v3.4` 进行 MaixCAM / MaixCAM Pro 转换，不需要再手动进入 Docker 安装 `tpu_mlir`。

## 6. 可选：使用脚本辅助部署转换镜像

建议优先按照第 4 节和第 5 节手动部署镜像。只有在熟悉 Docker、需要重复部署环境或排查镜像名称时，再考虑使用项目提供的辅助脚本：

该脚本使用 Bash，适用于 Linux、macOS 和 WSL。原生 Windows PowerShell / CMD 用户建议继续使用前面的手动部署流程，不需要运行这个脚本。

```bash
scripts/setup_toolchains.sh
```

脚本可以检查、导入、下载、构建和验证 Pulsar2 / TPU-MLIR 镜像。查看具体参数：

```bash
scripts/setup_toolchains.sh --help
```

如果已经准备好本地镜像包，可以让脚本辅助导入：

```bash
scripts/setup_toolchains.sh pulsar2 --pulsar2-tar /path/to/ax_pulsar2_6.0.tar.gz
scripts/setup_toolchains.sh tpumlir --tpuc-dev-tar /path/to/tpuc_dev_v3.4.tar.gz
```

已经按照前面的手动流程成功部署并验证镜像后，不需要再次运行该脚本。自动下载依赖外部链接和网络环境，稳定性通常不如手动下载并执行 `docker load`，因此不作为默认推荐方式。

## 7. 启动网页端

进入项目目录并激活前面准备好的 conda 或 venv 环境。下面这条命令在 Linux、macOS 和 Windows 中都可以使用，也是最直接的启动方式：

```bash
python -m uvicorn web.app:app --host 127.0.0.1 --port 8000
```

启动后浏览器打开：

```text
http://127.0.0.1:8000/
```

项目也提供了对应平台的便捷启动脚本。它们会优先使用项目目录里的 `.venv` 或 `venv`，否则使用当前环境中的 Python。

Linux / macOS / WSL：

```bash
./start.sh
```

Windows CMD：

```bat
start.bat
```

Windows PowerShell：

```powershell
.\start.ps1
```

如果 PowerShell 执行策略阻止运行 `.ps1`，直接使用 `start.bat` 即可；`start.bat` 会以仅对本次启动生效的方式调用 PowerShell，不修改系统执行策略。

### 局域网访问

默认只监听本机。如果需要让局域网内的其他电脑访问，可以设置 `HOST=0.0.0.0` 后运行对应平台的启动脚本。

Linux / macOS / WSL：

```bash
HOST=0.0.0.0 ./start.sh
```

Windows CMD：

```bat
set HOST=0.0.0.0
start.bat
```

Windows PowerShell：

```powershell
$env:HOST = "0.0.0.0"
.\start.ps1
```

监听非本机地址时，启动脚本会自动生成访问令牌，并打印带 `?token=...` 的首次访问地址。也可以提前设置 `MAIX_API_TOKEN` 使用固定令牌。API 客户端可以使用 `Authorization: Bearer <token>`。局域网环境仍建议通过可信网络或 HTTPS 反向代理使用。

Windows 原生环境需要安装 Docker Desktop，并保持 Docker Desktop 正在运行。项目目录需要位于 Docker Desktop 可以访问的磁盘中，建议放在你自己的工作区目录，并使用纯英文短路径。

### 运行配置

普通个人使用或单机部署时，**不需要设置下面的环境变量**，直接使用启动脚本即可。默认情况下同时只执行一个转换任务，其余任务会自动排队。模型转换会占用较多内存，因此没有确认机器资源充足前，建议保持 `MAIX_MAX_CONCURRENT_JOBS=1`。

只有遇到以下情况时才需要调整：

- 上传的正常模型或数据集超过默认大小限制。
- 可信数据集解压后超过默认限制。
- 服务器有充足的 CPU、内存和 Docker 资源，需要并行执行多个任务。
- 排查问题时确实需要保留或查看更多日志。

可用配置如下。容量相关变量的单位都是 MB：

| 环境变量 | 默认值 | 作用 | 什么时候调整 |
|----------|--------|------|--------------|
| `MAIX_MAX_CONCURRENT_JOBS` | `1` | 同时执行的转换任务数，超出的任务进入队列 | 仅在内存和 CPU 充足时调大；每增加一个并发任务都会额外启动一套转换流程和容器 |
| `MAIX_MAX_MODEL_MB` | `1024` | 单个模型上传大小上限 | 合法的 `.pt` 或 `.onnx` 文件超过 1 GB 时调大 |
| `MAIX_MAX_DATASET_MB` | `4096` | 单个量化数据集 zip 上传大小上限 | 合法数据集压缩包超过 4 GB 时调大 |
| `MAIX_MAX_ZIP_ENTRIES` | `20000` | zip 内文件和目录的数量上限 | 可信数据集确实包含超过 20000 个条目时调大 |
| `MAIX_MAX_ZIP_UNCOMPRESSED_MB` | `12288` | zip 解压后全部内容的总大小上限 | 可信数据集解压后超过 12 GB 时调大 |
| `MAIX_MAX_ZIP_FILE_MB` | `1024` | zip 内单个文件的解压大小上限 | zip 内确实存在超过 1 GB 的合法文件时调大，普通图片数据集一般不需要修改 |
| `MAIX_MAX_ZIP_COMPRESSION_RATIO` | `200` | zip 内单个文件允许的最大压缩比 | 可信压缩包被误判为异常高压缩比时再调大 |
| `MAIX_MAX_API_LOG_MB` | `64` | 网页服务侧单个任务日志的保存上限 | 调试时任务日志被截断，并且磁盘空间充足时调大 |
| `MAIX_MAX_CONVERSION_LOG_MB` | `64` | 转换工具单个步骤日志的保存上限 | 转换日志被截断且需要完整输出排查问题时调大 |
| `MAIX_MAX_LOG_RESPONSE_MB` | `8` | 网页一次读取的日志内容上限 | 网页中需要查看更长日志时调大；数值过大会增加网络传输和浏览器内存占用 |

zip 相关限制用于防止异常压缩包耗尽磁盘或内存。除非数据集来源可信并且确认机器资源足够，否则不建议提高这些限制。

环境变量必须在启动网页服务前设置。下面以“允许两个任务并发，并将数据集上传上限调整为 8 GB”为例。

Linux / macOS / WSL，仅对本次启动生效：

```bash
MAIX_MAX_CONCURRENT_JOBS=2 MAIX_MAX_DATASET_MB=8192 ./start.sh
```

也可以先在当前终端设置，再启动：

```bash
export MAIX_MAX_CONCURRENT_JOBS=2
export MAIX_MAX_DATASET_MB=8192
./start.sh
```

Windows CMD，仅对当前 CMD 窗口生效：

```bat
set MAIX_MAX_CONCURRENT_JOBS=2
set MAIX_MAX_DATASET_MB=8192
start.bat
```

Windows PowerShell，仅对当前 PowerShell 窗口生效：

```powershell
$env:MAIX_MAX_CONCURRENT_JOBS = "2"
$env:MAIX_MAX_DATASET_MB = "8192"
.\start.ps1
```

关闭对应终端后，这些临时设置会失效，下次启动会恢复默认值。修改配置后如果服务已经在运行，需要先停止服务，再从设置了环境变量的终端重新启动。

网页界面使用普通 HTML / CSS / JavaScript 静态文件，不需要 npm 或前端构建步骤。

## 8. 准备上传文件

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

## 9. 网页选项说明

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

当前支持的是 Detect 任务，不包含 pose、seg、obb。YOLO11 和 YOLOv8 的 `.pt -> .onnx` 导出使用当前 Python 环境里的 `ultralytics` 包；如果上传 `.onnx`，平台会直接使用 ONNX 进入后续转换。

| 选项 | `.mud` model_type | Detect 输出节点 |
|------|-------------------|-----------------|
| YOLO26 | `yolo26` | 6 个 `one2one_cv2 / one2one_cv3` 输出 |
| YOLO11 | `yolo11` | `/model.23/dfl/conv/Conv_output_0` 和 `/model.23/Sigmoid_output_0` |
| YOLOv8 | `yolov8` | `/model.22/dfl/conv/Conv_output_0` 和 `/model.22/Sigmoid_output_0` |

这里的 YOLO11 / YOLOv8 Detect 节点选择对应 MaixPy 文档里的方案二。它会让更多计算进入模型参与量化，适合 MaixCAM / MaixCAM Pro；当前平台也用这套节点生成 MaixCam2 模型。

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

## 10. 开始转换和下载结果

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

如果目标设备选择的是 MaixCAM / MaixCAM Pro，zip 里会包含：

```text
model_name.mud
model_name.cvimodel
```

把这两个文件放到 MaixCAM / MaixCAM Pro 的同一个目录中，然后在 MaixPy 代码里加载 `.mud`。

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

## 11. 任务目录和自动清理

程序自身产生的运行文件默认都保存在项目目录中：

```text
maix_converter_platform/
  jobs/       # 上传文件、转换中间文件、日志和结果
  runtime/    # Web 上传临时文件
  downloads/  # 可选辅助脚本下载的镜像包
```

Ultralytics、Torch、Matplotlib 等转换阶段可能产生的配置和缓存会写入对应任务的 `jobs/<job_id>/runtime/`，不会主动在 Windows 的磁盘根目录或用户配置目录创建项目运行文件。

Docker 镜像和 Docker Desktop 自身的数据仍由 Docker 管理，保存位置取决于 Docker Desktop 配置，不属于项目创建的运行文件。

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
