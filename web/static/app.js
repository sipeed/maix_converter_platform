(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);

  const messages = {
    "zh-CN": {
      "app.subtitle": "MaixCam / MaixCam2 模型转换工作台",
      "app.language": "语言",
      "actions.theme": "主题",
      "actions.darkMode": "深色",
      "actions.lightMode": "浅色",
      "actions.startConvert": "开始转换",
      "actions.refresh": "刷新",
      "actions.cancel": "取消任务",
      "actions.downloadResult": "下载结果",
      "actions.copyLog": "复制日志",
      "actions.downloadLog": "下载日志",
      "actions.clearDisplay": "清空显示",
      "actions.autoScroll": "自动滚动",
      "actions.updateList": "更新列表",
      "actions.view": "查看",
      "actions.delete": "删除",
      "server.checking": "API 检查中",
      "server.online": "API 在线",
      "server.offline": "API 离线",
      "server.reconnecting": "API 重连中",
      "jobForm.eyebrow": "新建任务",
      "jobForm.title": "转换任务",
      "jobForm.filesGroup": "输入文件",
      "jobForm.targetGroup": "目标平台",
      "jobForm.paramsGroup": "转换参数",
      "jobForm.modelFile": "模型文件",
      "jobForm.modelName": "模型名称",
      "jobForm.modelChoose": "选择模型",
      "jobForm.modelHelp": "支持 .pt / .onnx",
      "jobForm.datasetFile": "量化数据集",
      "jobForm.datasetChoose": "选择数据集",
      "jobForm.datasetHelp": "上传 .zip 文件",
      "jobForm.dragHint": "点击选择，或拖拽文件到这里",
      "jobForm.target": "目标设备",
      "jobForm.yoloVersion": "YOLO 版本",
      "jobForm.imagesNum": "图片数量",
      "jobForm.fastMode": "快速模式",
      "jobForm.width": "宽度",
      "jobForm.height": "高度",
      "upload.progressAria": "上传进度",
      "upload.waiting": "等待上传",
      "upload.uploading": "正在上传 {percent}%",
      "upload.failed": "上传失败",
      "upload.done": "上传完成，转换任务已创建",
      "monitor.eyebrow": "实时状态",
      "monitor.title": "任务监控",
      "monitor.model": "模型",
      "monitor.doneAt": "完成时间",
      "monitor.config": "配置",
      "status.notStarted": "未开始",
      "status.queued": "排队中",
      "status.running": "转换中",
      "status.success": "已完成",
      "status.failed": "失败",
      "status.cancelled": "已取消",
      "status.unknown": "未知",
      "stage.prepare": "数据集准备",
      "stage.export": "ONNX 导出",
      "stage.prebuild": "任务准备",
      "stage.convert": "模型转换",
      "stage.package": "打包结果",
      "stage.progress.maixcam2": "MaixCam2 转换流程",
      "stage.progress.maixcam": "MaixCAM / Pro 转换流程",
      "stage.maixcam2.prepare": "数据准备",
      "stage.maixcam2.export": "ONNX 导出",
      "stage.maixcam2.prebuild": "Pulsar 配置",
      "stage.maixcam2.convert": "Pulsar2 编译",
      "stage.maixcam2.package": "AXModel 打包",
      "stage.maixcam.prepare": "数据准备",
      "stage.maixcam.export": "ONNX 导出",
      "stage.maixcam.prebuild": "MLIR 配置",
      "stage.maixcam.convert": "量化部署",
      "stage.maixcam.package": "CVIModel 打包",
      "stage.skipped": "已跳过",
      "log.waiting": "等待任务输出...",
      "log.cleared": "日志已清空，等待新输出...",
      "log.copied": "日志已复制",
      "log.copyFailed": "复制失败，请手动选择日志",
      "log.connectError": "日志连接异常",
      "jobs.eyebrow": "历史记录",
      "jobs.title": "最近任务",
      "jobs.count": "{visible} / {total} 个任务",
      "jobs.empty": "暂无任务",
      "jobs.noMatch": "没有匹配的任务",
      "jobs.viewing": "正在查看任务 {jobId}",
      "filter.all": "全部",
      "filter.running": "运行中",
      "filter.success": "已完成",
      "filter.failed": "失败",
      "filter.cancelled": "已取消",
      "validation.model": "请选择 .pt 或 .onnx 模型文件",
      "validation.dataset": "请上传 .zip 量化数据集",
      "validation.dragOneFile": "每次只能拖入一个文件",
      "validation.size": "宽度和高度必须是 32 到 4096 之间的 32 倍数",
      "error.uploadFailed": "上传失败",
      "error.network": "网络请求失败",
      "error.noCurrentJob": "当前没有任务",
      "auth.tokenPrompt": "请输入转换平台访问令牌",
      "auth.required": "需要有效的访问令牌",
      "confirm.cancel": "确定取消任务 {jobId}？",
      "confirm.delete": "删除任务 {jobId}？任务目录和转换结果都会被删除。",
      "toast.jobCreated": "转换任务已创建",
      "toast.jobCancelled": "任务已取消",
      "toast.jobDeleted": "任务已删除",
      "config.images": "{count} 张",
      "config.fast": "快速",
      "config.full": "完整",
    },
    "en-US": {
      "app.subtitle": "MaixCam / MaixCam2 model conversion workspace",
      "app.language": "Language",
      "actions.theme": "Theme",
      "actions.darkMode": "Dark",
      "actions.lightMode": "Light",
      "actions.startConvert": "Start conversion",
      "actions.refresh": "Refresh",
      "actions.cancel": "Cancel job",
      "actions.downloadResult": "Download result",
      "actions.copyLog": "Copy log",
      "actions.downloadLog": "Download log",
      "actions.clearDisplay": "Clear view",
      "actions.autoScroll": "Auto-scroll",
      "actions.updateList": "Update list",
      "actions.view": "View",
      "actions.delete": "Delete",
      "server.checking": "Checking API",
      "server.online": "API online",
      "server.offline": "API offline",
      "server.reconnecting": "Reconnecting API",
      "jobForm.eyebrow": "New job",
      "jobForm.title": "Conversion job",
      "jobForm.filesGroup": "Input files",
      "jobForm.targetGroup": "Target platform",
      "jobForm.paramsGroup": "Conversion parameters",
      "jobForm.modelFile": "Model file",
      "jobForm.modelName": "Model name",
      "jobForm.modelChoose": "Choose model",
      "jobForm.modelHelp": "Supports .pt / .onnx",
      "jobForm.datasetFile": "Calibration dataset",
      "jobForm.datasetChoose": "Choose dataset",
      "jobForm.datasetHelp": "Upload a .zip file",
      "jobForm.dragHint": "Click to choose, or drag a file here",
      "jobForm.target": "Target device",
      "jobForm.yoloVersion": "YOLO version",
      "jobForm.imagesNum": "Image count",
      "jobForm.fastMode": "Fast mode",
      "jobForm.width": "Width",
      "jobForm.height": "Height",
      "upload.progressAria": "Upload progress",
      "upload.waiting": "Waiting to upload",
      "upload.uploading": "Uploading {percent}%",
      "upload.failed": "Upload failed",
      "upload.done": "Upload complete, conversion job created",
      "monitor.eyebrow": "Live status",
      "monitor.title": "Job monitor",
      "monitor.model": "Model",
      "monitor.doneAt": "Completed",
      "monitor.config": "Config",
      "status.notStarted": "Not started",
      "status.queued": "Queued",
      "status.running": "Converting",
      "status.success": "Completed",
      "status.failed": "Failed",
      "status.cancelled": "Cancelled",
      "status.unknown": "Unknown",
      "stage.prepare": "Prepare dataset",
      "stage.export": "Export ONNX",
      "stage.prebuild": "Prepare job",
      "stage.convert": "Convert model",
      "stage.package": "Package result",
      "stage.progress.maixcam2": "MaixCam2 conversion flow",
      "stage.progress.maixcam": "MaixCAM / Pro conversion flow",
      "stage.maixcam2.prepare": "Prepare data",
      "stage.maixcam2.export": "Export ONNX",
      "stage.maixcam2.prebuild": "Pulsar config",
      "stage.maixcam2.convert": "Pulsar2 build",
      "stage.maixcam2.package": "Package AXModel",
      "stage.maixcam.prepare": "Prepare data",
      "stage.maixcam.export": "Export ONNX",
      "stage.maixcam.prebuild": "MLIR config",
      "stage.maixcam.convert": "Quantize & deploy",
      "stage.maixcam.package": "Package CVIModel",
      "stage.skipped": "Skipped",
      "log.waiting": "Waiting for job output...",
      "log.cleared": "Log cleared. Waiting for new output...",
      "log.copied": "Log copied",
      "log.copyFailed": "Copy failed. Select the log manually.",
      "log.connectError": "Log connection error",
      "jobs.eyebrow": "History",
      "jobs.title": "Recent jobs",
      "jobs.count": "{visible} / {total} jobs",
      "jobs.empty": "No jobs yet",
      "jobs.noMatch": "No matching jobs",
      "jobs.viewing": "Viewing job {jobId}",
      "filter.all": "All",
      "filter.running": "Running",
      "filter.success": "Completed",
      "filter.failed": "Failed",
      "filter.cancelled": "Cancelled",
      "validation.model": "Choose a .pt or .onnx model file",
      "validation.dataset": "Upload a .zip calibration dataset",
      "validation.dragOneFile": "Drop one file at a time",
      "validation.size": "Width and height must be multiples of 32 between 32 and 4096",
      "error.uploadFailed": "Upload failed",
      "error.network": "Network request failed",
      "error.noCurrentJob": "No current job",
      "auth.tokenPrompt": "Enter the converter access token",
      "auth.required": "A valid access token is required",
      "confirm.cancel": "Cancel job {jobId}?",
      "confirm.delete": "Delete job {jobId}? The job directory and conversion result will be removed.",
      "toast.jobCreated": "Conversion job created",
      "toast.jobCancelled": "Job cancelled",
      "toast.jobDeleted": "Job deleted",
      "config.images": "{count} images",
      "config.fast": "Fast",
      "config.full": "Full",
    },
  };

  const state = {
    currentJobId: "",
    currentJob: null,
    currentFilter: "all",
    jobs: [],
    socket: null,
    logText: "",
    logPlaceholderKey: "log.waiting",
    language: "zh-CN",
    serverState: "checking",
    uploadPercent: 0,
    uploadTextKey: "upload.waiting",
    uploadTextParams: {},
    downloadedJobIds: new Set(),
    openRequestId: 0,
  };
  let uploadHideTimer = 0;
  let authPromptPromise = null;

  const stageOrder = ["prepare", "export", "prebuild", "convert", "package"];
  const maxLogChars = 5_000_000;
  const targetSizeDefaults = {
    maixcam2: [640, 480],
    maixcam: [320, 224],
  };
  const stageActiveIndex = {
    prepare_done: 1,
    exporting: 1,
    export_done: 2,
    prebuilding: 2,
    prebuild_done: 3,
    pulsar2: 3,
    pulsar2_done: 4,
    tpumlir: 3,
    tpumlir_done: 4,
    packaging: 4,
    done: 4,
  };

  document.addEventListener("DOMContentLoaded", init);

  async function init() {
    restoreTheme();
    restoreLanguage();
    bindEvents();
    updateToolchainBadge(document.querySelector('input[name="target"]:checked')?.value);
    applyI18n();
    updateStageLabels(document.querySelector('input[name="target"]:checked')?.value);
    updateThemeButton();
    setServerState("checking");
    const token = consumeApiTokenFromUrl();
    if (token) {
      try {
        await establishApiSession(token);
      } catch (error) {
        showToast(error.message);
      }
    }
    if (await checkHealth()) {
      await loadJobs();
      subscribeJobs();
    }
  }

  function bindEvents() {
    $("languageSelectButton").addEventListener("click", () => {
      setLanguageMenuOpen($("languageSelectMenu").hidden);
    });
    $("languageSelectButton").addEventListener("keydown", handleLanguageButtonKeydown);
    document.querySelectorAll("#languageSelectControl .language-option").forEach((option) => {
      option.addEventListener("click", () => selectLanguageOption(option));
      option.addEventListener("keydown", (event) => handleLanguageOptionKeydown(event, option));
    });
    $("themeButton").addEventListener("click", toggleTheme);
    $("jobForm").addEventListener("submit", submitJob);
    $("modelFile").addEventListener("change", updateModelName);
    $("datasetFile").addEventListener("change", updateDatasetFileHelp);
    document.querySelectorAll('input[name="target"]').forEach((input) => {
      input.addEventListener("change", updateTargetDefaults);
    });
    $("yoloSelectButton").addEventListener("click", () => {
      setYoloMenuOpen($("yoloSelectMenu").hidden);
    });
    $("yoloSelectButton").addEventListener("keydown", handleYoloButtonKeydown);
    document.querySelectorAll("#yoloSelect .select-option").forEach((option) => {
      option.addEventListener("click", () => selectYoloOption(option));
      option.addEventListener("keydown", (event) => handleYoloOptionKeydown(event, option));
    });
    document.addEventListener("click", (event) => {
      if (!$("yoloSelect").contains(event.target)) setYoloMenuOpen(false);
      if (!$("languageSelectControl").contains(event.target)) setLanguageMenuOpen(false);
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        setYoloMenuOpen(false);
        setLanguageMenuOpen(false);
      }
    });
    bindUploadDropZone("modelFile", /\.(pt|onnx)$/i, "validation.model", updateModelName);
    bindUploadDropZone("datasetFile", /\.zip$/i, "validation.dataset", updateDatasetFileHelp);
    $("refreshButton").addEventListener("click", refreshCurrentJob);
    $("reloadJobs").addEventListener("click", loadJobs);
    $("cancelJobButton").addEventListener("click", cancelCurrentJob);
    $("logCopyBtn").addEventListener("click", copyLog);
    $("logDownloadBtn").addEventListener("click", downloadLog);
    $("logClearBtn").addEventListener("click", () => clearLog());
    $("downloadButton").addEventListener("click", markResultDownloaded);
    $("jobsFilter").addEventListener("click", changeFilter);
  }

  function restoreTheme() {
    const theme = localStorage.getItem("maix_converter_theme") || "light";
    document.documentElement.dataset.theme = theme;
  }

  function toggleTheme() {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    localStorage.setItem("maix_converter_theme", next);
    updateThemeButton();
  }

  function updateThemeButton() {
    const dark = document.documentElement.dataset.theme === "dark";
    const button = $("themeButton");
    const label = t(dark ? "actions.lightMode" : "actions.darkMode");
    button.textContent = dark ? "☀" : "☾";
    button.title = label;
    button.setAttribute("aria-label", label);
  }

  function restoreLanguage() {
    const saved = localStorage.getItem("maix_converter_language");
    const browser = (navigator.language || "zh-CN").toLowerCase().startsWith("zh") ? "zh-CN" : "en-US";
    state.language = messages[saved] ? saved : browser;
    updateLanguageSelect(state.language);
  }

  function setLanguage(language) {
    if (!messages[language]) return;
    state.language = language;
    localStorage.setItem("maix_converter_language", language);
    updateLanguageSelect(language);
    setLanguageMenuOpen(false);
    applyI18n();
    updateThemeButton();
    setServerState(state.serverState);
    updateModelFileHelp();
    updateDatasetFileHelp();
    updateUploadDisplay();
    if (state.currentJob) {
      renderJob(state.currentJob);
    } else {
      updateStageLabels(document.querySelector('input[name="target"]:checked')?.value);
      setInitialJobStatus();
    }
    renderJobs();
    if (!state.logText) $("logView").textContent = t(state.logPlaceholderKey);
  }

  function applyI18n() {
    document.documentElement.lang = state.language;
    document.querySelectorAll("[data-i18n]").forEach((node) => {
      if (node.id === "jobStatus" && state.currentJob) return;
      if (node.id === "logView" && state.logText) return;
      if (node.id === "uploadProgressText") return;
      node.textContent = t(node.dataset.i18n);
    });
    document.querySelectorAll("[data-i18n-aria-label]").forEach((node) => {
      node.setAttribute("aria-label", t(node.dataset.i18nAriaLabel));
    });
  }

  function setLanguageMenuOpen(open) {
    $("languageSelectMenu").hidden = !open;
    $("languageSelectButton").setAttribute("aria-expanded", String(open));
    $("languageSelectControl").classList.toggle("open", open);
  }

  function updateLanguageSelect(language) {
    const option = document.querySelector(`#languageSelectControl .language-option[data-value="${language}"]`);
    $("languageSelect").value = language;
    $("languageSelectValue").textContent = option?.dataset.label || language;
    document.querySelectorAll("#languageSelectControl .language-option").forEach((item) => {
      const selected = item.dataset.value === language;
      item.classList.toggle("active", selected);
      item.setAttribute("aria-selected", String(selected));
    });
  }

  function selectLanguageOption(option) {
    setLanguage(option.dataset.value);
    $("languageSelectButton").focus();
  }

  function handleLanguageButtonKeydown(event) {
    if (!["ArrowDown", "Enter", " "].includes(event.key)) return;
    event.preventDefault();
    setLanguageMenuOpen(true);
    const active = document.querySelector("#languageSelectControl .language-option.active") || document.querySelector("#languageSelectControl .language-option");
    active?.focus();
  }

  function handleLanguageOptionKeydown(event, option) {
    const options = Array.from(document.querySelectorAll("#languageSelectControl .language-option"));
    const currentIndex = options.indexOf(option);
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const offset = event.key === "ArrowDown" ? 1 : -1;
      options[(currentIndex + offset + options.length) % options.length].focus();
    } else if (event.key === "Home" || event.key === "End") {
      event.preventDefault();
      options[event.key === "Home" ? 0 : options.length - 1].focus();
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      selectLanguageOption(option);
    }
  }

  function t(key, params = {}) {
    const table = messages[state.language] || messages["zh-CN"];
    const fallback = messages["zh-CN"][key] || key;
    return String(table[key] || fallback).replace(/\{(\w+)\}/g, (_, name) => {
      return params[name] ?? "";
    });
  }

  function consumeApiTokenFromUrl() {
    const url = new URL(window.location.href);
    const token = url.searchParams.get("token") || "";
    if (!token) return "";
    url.searchParams.delete("token");
    history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
    return token;
  }

  async function establishApiSession(token) {
    const res = await fetch("/api/session", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    return readResponse(res);
  }

  async function requestApiToken() {
    if (authPromptPromise) return authPromptPromise;
    authPromptPromise = Promise.resolve().then(async () => {
      const token = window.prompt(t("auth.tokenPrompt"))?.trim() || "";
      if (!token) return false;
      await establishApiSession(token);
      return true;
    });
    try {
      return await authPromptPromise;
    } catch (error) {
      showToast(error.message || t("auth.required"));
      return false;
    } finally {
      authPromptPromise = null;
    }
  }

  async function authorizedFetch(url, options = {}) {
    let res = await fetch(url, options);
    if (res.status !== 401) return res;
    if (!(await requestApiToken())) return res;
    return fetch(url, options);
  }

  async function checkHealth() {
    try {
      const res = await authorizedFetch("/api/health", { cache: "no-store" });
      await readResponse(res);
      setServerState("online");
      return true;
    } catch (error) {
      setServerState("offline");
      if (error.message) showToast(error.message);
      return false;
    }
  }

  function setServerState(kind) {
    state.serverState = kind;
    const node = $("serverState");
    const className = kind === "reconnecting" ? "checking" : kind;
    node.className = `server-state ${className}`;
    node.textContent = t(`server.${kind}`);
  }

  function setInitialJobStatus() {
    $("jobStatus").className = "status idle";
    $("jobStatus").textContent = t("status.notStarted");
  }

  function resetJobDisplay() {
    state.currentJob = null;
    $("jobId").textContent = "-";
    $("jobModel").textContent = "-";
    $("jobDone").textContent = "-";
    $("jobConfig").textContent = "-";
    $("jobError").hidden = true;
    $("jobError").textContent = "";
    $("cancelJobButton").hidden = true;
    $("downloadButton").classList.add("disabled");
    $("downloadButton").classList.remove("ready");
    $("downloadButton").setAttribute("aria-disabled", "true");
    $("downloadButton").href = "#";
    renderStages({ status: "unknown" });
    setInitialJobStatus();
  }

  function updateModelName() {
    const file = $("modelFile").files[0];
    if (!file) {
      updateModelFileHelp();
      return;
    }
    $("modelName").value = file.name.replace(/\.[^.]+$/, "");
    updateYoloVersionFromFileName(file.name);
    updateModelFileHelp();
  }

  function updateYoloVersionFromFileName(fileName) {
    const lower = fileName.toLowerCase();
    if (lower.includes("yolo11")) {
      setYoloVersion("yolo11", "YOLO11", "Detect");
    } else if (lower.includes("yolov8") || lower.includes("yolo8")) {
      setYoloVersion("yolov8", "YOLOv8", "Detect");
    } else if (lower.includes("yolo26")) {
      setYoloVersion("yolo26", "YOLO26", "Detect");
    }
  }

  function setYoloMenuOpen(open) {
    $("yoloSelectMenu").hidden = !open;
    $("yoloSelectButton").setAttribute("aria-expanded", String(open));
    $("yoloSelect").classList.toggle("open", open);
  }

  function setYoloVersion(value, label, meta) {
    $("yoloVersion").value = value;
    $("yoloSelectLabel").textContent = label || value;
    $("yoloSelectMeta").textContent = meta || "Detect";
    document.querySelectorAll("#yoloSelect .select-option").forEach((option) => {
      const selected = option.dataset.value === value;
      option.classList.toggle("active", selected);
      option.setAttribute("aria-selected", String(selected));
    });
  }

  function selectYoloOption(option) {
    setYoloVersion(option.dataset.value, option.dataset.label, option.dataset.meta);
    setYoloMenuOpen(false);
    $("yoloSelectButton").focus();
  }

  function handleYoloButtonKeydown(event) {
    if (!["ArrowDown", "Enter", " "].includes(event.key)) return;
    event.preventDefault();
    setYoloMenuOpen(true);
    const active = document.querySelector("#yoloSelect .select-option.active") || document.querySelector("#yoloSelect .select-option");
    active?.focus();
  }

  function handleYoloOptionKeydown(event, option) {
    const options = Array.from(document.querySelectorAll("#yoloSelect .select-option"));
    const currentIndex = options.indexOf(option);
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const offset = event.key === "ArrowDown" ? 1 : -1;
      options[(currentIndex + offset + options.length) % options.length].focus();
    } else if (event.key === "Home" || event.key === "End") {
      event.preventDefault();
      options[event.key === "Home" ? 0 : options.length - 1].focus();
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      selectYoloOption(option);
    }
  }

  function updateTargetDefaults(event) {
    const input = event.currentTarget;
    if (!input.checked) return;
    const size = targetSizeDefaults[input.value];
    if (!size) return;
    $("imgszWidth").value = String(size[0]);
    $("imgszHeight").value = String(size[1]);
    updateToolchainBadge(input.value);
    if (!state.currentJob) updateStageLabels(input.value);
  }

  function updateToolchainBadge(target) {
    $("toolchainBadge").textContent = target === "maixcam" ? "TPU-MLIR" : "Pulsar2";
  }

  function updateStageLabels(target) {
    const workflow = target === "maixcam" ? "maixcam" : "maixcam2";
    $("stageProgress").setAttribute("aria-label", t(`stage.progress.${workflow}`));
    for (const stage of stageOrder) {
      $(`stageLabel${stage[0].toUpperCase()}${stage.slice(1)}`).textContent = t(`stage.${workflow}.${stage}`);
    }
  }

  function updateModelFileHelp() {
    const file = $("modelFile").files[0];
    $("modelFileHelp").textContent = file ? file.name : t("jobForm.modelHelp");
  }

  function updateDatasetFileHelp() {
    const file = $("datasetFile").files[0];
    $("datasetFileHelp").textContent = file ? file.name : t("jobForm.datasetHelp");
  }

  function bindUploadDropZone(inputId, pattern, errorKey, onChange) {
    const input = $(inputId);
    const field = input.closest(".upload-field");
    if (!field) return;

    ["dragenter", "dragover"].forEach((eventName) => {
      field.addEventListener(eventName, (event) => {
        event.preventDefault();
        event.stopPropagation();
        field.classList.add("drag-over");
      });
    });

    ["dragleave", "dragend", "drop"].forEach((eventName) => {
      field.addEventListener(eventName, (event) => {
        event.preventDefault();
        event.stopPropagation();
        if (eventName !== "dragenter") field.classList.remove("drag-over");
      });
    });

    field.addEventListener("drop", (event) => {
      const files = Array.from(event.dataTransfer?.files || []);
      if (files.length !== 1) {
        showToast(t("validation.dragOneFile"));
        return;
      }
      const file = files[0];
      if (!pattern.test(file.name)) {
        showToast(t(errorKey));
        return;
      }
      const transfer = new DataTransfer();
      transfer.items.add(file);
      input.files = transfer.files;
      onChange();
    });
  }

  function validateForm() {
    const model = $("modelFile").files[0];
    const dataset = $("datasetFile").files[0];
    if (!model || !/\.(pt|onnx)$/i.test(model.name)) {
      throw new Error(t("validation.model"));
    }
    if (!dataset || !/\.zip$/i.test(dataset.name)) {
      throw new Error(t("validation.dataset"));
    }
    for (const id of ["imgszWidth", "imgszHeight"]) {
      const value = Number($(id).value);
      if (!Number.isInteger(value) || value < 32 || value > 4096 || value % 32 !== 0) {
        throw new Error(t("validation.size"));
      }
    }
  }

  function submitJob(event) {
    event.preventDefault();
    try {
      validateForm();
    } catch (error) {
      showToast(error.message);
      return;
    }

    const data = new FormData($("jobForm"));
    const submitButton = $("submitButton");
    submitButton.disabled = true;
    showUploadProgress();
    setUploadProgress(0, "upload.uploading", { percent: 0 });

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/jobs");
    xhr.upload.onprogress = (event) => {
      if (!event.lengthComputable) return;
      const percent = Math.round((event.loaded / event.total) * 100);
      setUploadProgress(percent, "upload.uploading", { percent });
    };
    xhr.onload = () => {
      submitButton.disabled = false;
      if (xhr.status < 200 || xhr.status >= 300) {
        setUploadProgress(0, "upload.failed");
        hideUploadProgress(1800);
        showToast(readXhrError(xhr));
        return;
      }
      const payload = JSON.parse(xhr.responseText);
      setUploadProgress(100, "upload.done");
      hideUploadProgress(900);
      showToast(t("toast.jobCreated"));
      openJob(payload.job_id, { quiet: true });
      loadJobs();
    };
    xhr.onerror = () => {
      submitButton.disabled = false;
      setUploadProgress(0, "upload.failed");
      hideUploadProgress(1800);
      showToast(t("error.network"));
    };
    xhr.onabort = () => {
      submitButton.disabled = false;
      setUploadProgress(0, "upload.failed");
      hideUploadProgress(1800);
    };
    xhr.send(data);
  }

  function showUploadProgress() {
    clearTimeout(uploadHideTimer);
    $("uploadProgressBar").closest(".progress").classList.add("active");
    $("uploadProgressText").classList.add("active");
  }

  function hideUploadProgress(delay = 0) {
    clearTimeout(uploadHideTimer);
    uploadHideTimer = window.setTimeout(() => {
      $("uploadProgressBar").closest(".progress").classList.remove("active");
      $("uploadProgressText").classList.remove("active");
      state.uploadPercent = 0;
      $("uploadProgressBar").style.width = "0%";
    }, delay);
  }

  function setUploadProgress(percent, key, params = {}) {
    state.uploadPercent = percent;
    state.uploadTextKey = key;
    state.uploadTextParams = params;
    updateUploadDisplay();
  }

  function updateUploadDisplay() {
    $("uploadProgressBar").style.width = `${state.uploadPercent}%`;
    $("uploadProgressText").textContent = t(state.uploadTextKey, state.uploadTextParams);
  }

  function readXhrError(xhr) {
    try {
      const payload = JSON.parse(xhr.responseText);
      return payload.detail || t("error.uploadFailed");
    } catch (error) {
      return xhr.responseText || t("error.uploadFailed");
    }
  }

  async function loadJobs() {
    try {
      const payload = await apiGet("/api/jobs");
      state.jobs = payload.jobs || [];
      renderJobs();
    } catch (error) {
      showToast(error.message);
    }
  }

  function subscribeJobs() {
    if (!window.EventSource) return;
    const events = new EventSource("/api/jobs/events");
    events.addEventListener("jobs", (event) => {
      const payload = JSON.parse(event.data);
      state.jobs = payload.jobs || [];
      renderJobs();
    });
    events.onerror = () => setServerState("reconnecting");
    events.onopen = () => setServerState("online");
  }

  function changeFilter(event) {
    const button = event.target.closest("[data-filter]");
    if (!button) return;
    state.currentFilter = button.dataset.filter;
    document.querySelectorAll(".filter").forEach((item) => item.classList.toggle("active", item === button));
    renderJobs();
  }

  function renderJobs() {
    const list = $("jobsList");
    const jobs = filterJobs(state.jobs);
    $("jobsCount").textContent = t("jobs.count", { visible: jobs.length, total: state.jobs.length });
    list.innerHTML = "";
    if (!jobs.length) {
      const empty = document.createElement("p");
      empty.className = "progress-text";
      empty.textContent = state.jobs.length ? t("jobs.noMatch") : t("jobs.empty");
      list.appendChild(empty);
      return;
    }
    for (const job of jobs) {
      list.appendChild(renderJobCard(job));
    }
  }

  function filterJobs(jobs) {
    if (state.currentFilter === "all") return jobs;
    if (state.currentFilter === "running") {
      return jobs.filter((job) => ["queued", "running"].includes(job.status));
    }
    return jobs.filter((job) => job.status === state.currentFilter);
  }

  function renderJobCard(job) {
    const card = document.createElement("article");
    card.className = "job-card";
    card.innerHTML = `
      <strong title="${escapeHtml(job.job_id)}">${escapeHtml(job.job_id)}</strong>
      <span>${escapeHtml(job.model_name || "-")}</span>
      <span>${escapeHtml(job.yolo_version || "-")}</span>
      <span>${escapeHtml(formatTarget(job.target))}</span>
      <span>${escapeHtml(statusLabel(job.status))}</span>
      <div class="job-card-actions"></div>
    `;

    const actions = card.querySelector(".job-card-actions");
    const view = document.createElement("button");
    view.className = "secondary-button";
    view.type = "button";
    view.textContent = t("actions.view");
    view.addEventListener("click", () => openJob(job.job_id));
    actions.appendChild(view);

    const remove = document.createElement("button");
    remove.className = "danger-button";
    remove.type = "button";
    remove.textContent = t("actions.delete");
    remove.disabled = ["queued", "running"].includes(job.status);
    remove.addEventListener("click", () => deleteJob(job.job_id));
    actions.appendChild(remove);

    return card;
  }

  async function openJob(jobId, options = {}) {
    if (!jobId) return;
    const requestId = ++state.openRequestId;
    closeLogSocket();
    state.currentJobId = jobId;
    resetJobDisplay();
    clearLog("log.waiting");
    try {
      const job = await apiGet(`/api/jobs/${encodeURIComponent(jobId)}`);
      if (requestId !== state.openRequestId || state.currentJobId !== jobId) return;
      renderJob(job);
      connectLog(jobId, requestId);
      if (!options.quiet) showToast(t("jobs.viewing", { jobId }));
    } catch (error) {
      if (requestId !== state.openRequestId || state.currentJobId !== jobId) return;
      state.currentJobId = "";
      resetJobDisplay();
      showToast(error.message);
    }
  }

  async function refreshCurrentJob() {
    if (!state.currentJobId) {
      showToast(t("error.noCurrentJob"));
      return;
    }
    const jobId = state.currentJobId;
    try {
      const job = await apiGet(`/api/jobs/${encodeURIComponent(jobId)}`);
      if (state.currentJobId !== jobId) return;
      renderJob(job);
    } catch (error) {
      showToast(error.message);
    }
  }

  function renderJob(job) {
    state.currentJob = job;
    state.currentJobId = job.job_id || state.currentJobId;
    const status = job.status || "unknown";
    $("jobStatus").className = `status ${status}`;
    $("jobStatus").textContent = statusLabel(status);
    $("jobId").textContent = job.job_id || "-";
    $("jobModel").textContent = job.model_name || "-";
    $("jobDone").textContent = formatTime(job.completed_at);
    $("jobConfig").textContent = [
      job.yolo_version || "-",
      formatTarget(job.target),
      Array.isArray(job.imgsz) ? job.imgsz.join("x") : "",
      job.images_num ? t("config.images", { count: job.images_num }) : "",
      job.fast ? t("config.fast") : t("config.full"),
    ].filter(Boolean).join(" / ");

    const jobMessage = job.error || job.cleanup_warning || "";
    $("jobError").hidden = !jobMessage;
    $("jobError").textContent = jobMessage;

    const active = ["queued", "running"].includes(status);
    $("cancelJobButton").hidden = !active;
    const canDownload = status === "success";
    const shouldHighlightDownload = canDownload && !state.downloadedJobIds.has(job.job_id);
    $("downloadButton").classList.toggle("disabled", !canDownload);
    $("downloadButton").classList.toggle("ready", shouldHighlightDownload);
    $("downloadButton").setAttribute("aria-disabled", String(!canDownload));
    $("downloadButton").href = canDownload ? `/api/jobs/${encodeURIComponent(job.job_id)}/download` : "#";
    renderStages(job);
  }

  function statusLabel(status) {
    return t(`status.${status || "unknown"}`);
  }

  function renderStages(job) {
    const status = job.status || "unknown";
    const stage = job.stage || "";
    const target = job.target || document.querySelector('input[name="target"]:checked')?.value || "maixcam2";
    const inputModel = String(job.input_model || "").toLowerCase();
    const onnxInput = job.input_suffix === ".onnx" || inputModel.endsWith(".onnx");
    let currentIndex = status === "queued" ? 0 : (stageActiveIndex[stage] ?? (status === "running" ? 0 : -1));
    if (onnxInput && currentIndex === 1 && stage !== "exporting") currentIndex = 2;
    updateStageLabels(target);

    document.querySelectorAll("#stageProgress [data-stage]").forEach((item) => {
      const index = stageOrder.indexOf(item.dataset.stage);
      const skipped = onnxInput && item.dataset.stage === "export";
      const finished = status === "success";
      item.classList.toggle("skipped", skipped);
      item.classList.toggle("done", !skipped && (finished || (currentIndex > index && currentIndex !== -1)));
      item.classList.toggle("active", !skipped && ["queued", "running"].includes(status) && index === currentIndex);
      item.classList.toggle("failed", !skipped && status === "failed" && index === currentIndex);
      item.classList.toggle("cancelled", !skipped && status === "cancelled" && index === currentIndex);
      item.title = skipped ? t("stage.skipped") : "";
    });
  }

  function closeLogSocket() {
    if (!state.socket) return;
    state.socket.close();
    state.socket = null;
  }

  function connectLog(jobId, requestId) {
    closeLogSocket();
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    const socket = new WebSocket(`${protocol}//${location.host}/api/jobs/${encodeURIComponent(jobId)}/stream`);
    state.socket = socket;
    socket.onmessage = (event) => {
      if (state.socket !== socket || requestId !== state.openRequestId || state.currentJobId !== jobId) return;
      const payload = JSON.parse(event.data);
      if (payload.type === "job") renderJob(payload.job);
      if (payload.type === "log") appendLog(payload.text);
      if (payload.type === "error") appendLog(`\n[error] ${payload.message}\n`);
      if (payload.type === "done") loadJobs();
    };
    socket.onerror = () => {
      if (state.socket === socket && requestId === state.openRequestId && state.currentJobId === jobId) {
        appendLog(`\n[${t("log.connectError")}]\n`);
      }
    };
    socket.onclose = () => {
      if (state.socket === socket) state.socket = null;
    };
  }

  function appendLog(text) {
    state.logText += text;
    if (state.logText.length > maxLogChars) {
      state.logText = `[earlier browser log output omitted]\n${state.logText.slice(-maxLogChars)}`;
    }
    $("logView").textContent = state.logText || t(state.logPlaceholderKey);
    if ($("logAutoScroll").checked) {
      $("logView").scrollTop = $("logView").scrollHeight;
    }
  }

  function clearLog(key = "log.cleared") {
    state.logText = "";
    state.logPlaceholderKey = key;
    $("logView").textContent = t(key);
  }

  async function copyLog() {
    try {
      await navigator.clipboard.writeText(state.logText || $("logView").textContent);
      showToast(t("log.copied"));
    } catch (error) {
      showToast(t("log.copyFailed"));
    }
  }

  function downloadLog() {
    const blob = new Blob([state.logText || $("logView").textContent], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${state.currentJobId || "maix-converter"}.log`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function markResultDownloaded() {
    if ($("downloadButton").classList.contains("disabled")) return;
    const jobId = state.currentJob?.job_id || state.currentJobId;
    if (jobId) state.downloadedJobIds.add(jobId);
    $("downloadButton").classList.remove("ready");
  }

  async function cancelCurrentJob() {
    const jobId = state.currentJob?.job_id;
    if (!jobId || jobId !== state.currentJobId) {
      showToast(t("error.noCurrentJob"));
      return;
    }
    if (!confirm(t("confirm.cancel", { jobId }))) return;
    try {
      const payload = await apiPost(`/api/jobs/${encodeURIComponent(jobId)}/cancel`);
      showToast(payload.cleanup_warning || t("toast.jobCancelled"));
      refreshCurrentJob();
      loadJobs();
    } catch (error) {
      showToast(error.message);
    }
  }

  async function deleteJob(jobId) {
    if (!confirm(t("confirm.delete", { jobId }))) return;
    try {
      await apiDelete(`/api/jobs/${encodeURIComponent(jobId)}`);
      showToast(t("toast.jobDeleted"));
      if (state.currentJobId === jobId) {
        state.openRequestId += 1;
        closeLogSocket();
        state.currentJobId = "";
        resetJobDisplay();
        clearLog("log.waiting");
      }
      loadJobs();
    } catch (error) {
      showToast(error.message);
    }
  }

  async function apiGet(url) {
    const res = await authorizedFetch(url, { cache: "no-store" });
    return readResponse(res);
  }

  async function apiPost(url) {
    const res = await authorizedFetch(url, { method: "POST" });
    return readResponse(res);
  }

  async function apiDelete(url) {
    const res = await authorizedFetch(url, { method: "DELETE" });
    return readResponse(res);
  }

  async function readResponse(res) {
    const text = await res.text();
    let payload = {};
    if (text) {
      try {
        payload = JSON.parse(text);
      } catch (error) {
        payload = { detail: text };
      }
    }
    if (!res.ok) throw new Error(payload.detail || res.statusText);
    return payload;
  }

  function formatTarget(target) {
    if (target === "maixcam2") return "MaixCam2";
    if (target === "maixcam") return "MaixCAM / Pro";
    return target || "-";
  }

  function formatTime(value) {
    if (!value) return "-";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString(state.language);
  }

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[char]));
  }

  let toastTimer = 0;
  function showToast(message) {
    const toast = $("toast");
    toast.textContent = message;
    toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toast.hidden = true;
    }, 2600);
  }
})();
