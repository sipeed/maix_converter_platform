(function () {
  "use strict";

  const storageKey = "maix_converter:language";
  const defaultLanguage = "zh-CN";
  const languages = {
    "zh-CN": "中文",
    "en-US": "English",
  };

  const zhToEn = {
    "模型转换工作台": "Model conversion workspace",
    "切换主题": "Toggle theme",
    "切换深色/浅色主题": "Toggle dark/light theme",
    "API 检查中": "Checking API",
    "API 在线": "API online",
    "API 重连中": "API reconnecting",
    "API 离线": "API offline",
    "在线": "Online",
    "重连中": "Reconnecting",
    "离线": "Offline",
    "转换任务": "Conversion task",
    "模型文件": "Model file",
    "松开上传模型文件": "Release to upload model file",
    "选择模型": "Choose model",
    "支持 .pt / .onnx（支持拖拽上传）": "Supports .pt / .onnx (drag and drop supported)",
    "量化数据集": "Quantization dataset",
    "松开上传数据集文件": "Release to upload dataset file",
    "上传数据集": "Upload dataset",
    "支持 .zip（支持拖拽上传）": "Supports .zip (drag and drop supported)",
    "目标设备": "Target device",
    "YOLO 版本": "YOLO version",
    "图片数量": "Image count",
    "快速模式": "Fast mode",
    "宽度": "Width",
    "高度": "Height",
    "开始转换": "Start conversion",
    "等待上传": "Waiting for upload",
    "任务监控": "Task monitor",
    "未开始": "Not started",
    "模型": "Model",
    "完成时间": "Completed at",
    "分辨率": "Resolution",
    "类别 / 量化图片": "Classes / calibration images",
    "模式": "Mode",
    "耗时": "Elapsed",
    "数据集准备": "Dataset preparation",
    "ONNX 导出": "ONNX export",
    "任务准备": "Task preparation",
    "Pulsar2 转换": "Pulsar2 conversion",
    "TPU-MLIR 转换": "TPU-MLIR conversion",
    "打包结果": "Package results",
    "刷新": "Refresh",
    "取消任务": "Cancel task",
    "任务完成后可下载": "Available after the task finishes",
    "下载结果": "Download results",
    "复制日志": "Copy log",
    "复制": "Copy",
    "下载日志": "Download log",
    "下载": "Download",
    "清空显示": "Clear display",
    "清空": "Clear",
    "自动滚动到底部": "Auto-scroll to bottom",
    "自动滚动": "Auto-scroll",
    "日志已截断，完整日志请下载": "Log truncated. Download the full log.",
    "等待任务输出...": "Waiting for task output...",
    "最近任务": "Recent tasks",
    "更新列表": "Update list",
    "全部": "All",
    "运行中": "Running",
    "已完成": "Completed",
    "失败": "Failed",
    "已取消": "Cancelled",
    "关闭通知": "Close notification",
    "日志连接已断开，正在尝试重连": "Log connection lost. Reconnecting.",
    "日志连接已恢复": "Log connection restored.",
    "任务推送连接异常，正在重连": "Task update connection failed. Reconnecting.",
    "任务推送已恢复": "Task updates restored.",
    "确认": "Confirm",
    "取消": "Cancel",
    "日志已复制到剪贴板": "Log copied to clipboard.",
    "复制失败，请手动选择文本复制": "Copy failed. Select the text manually.",
    "日志已清空，等待新输出...": "Log cleared. Waiting for new output...",
    "正在运行的转换进程会被终止。": "The running conversion process will be terminated.",
    "任务已取消": "Task cancelled",
    "任务已取消。": "Task cancelled.",
    "快速": "Fast",
    "完整": "Full",
    "转换失败，请查看日志。": "Conversion failed. Check the log.",
    "日志连接已建立": "Log connection established",
    "任务已删除": "Task deleted",
    "排队中": "Queued",
    "转换中": "Converting",
    "未知": "Unknown",
    "暂无任务": "No tasks yet",
    "上传模型和数据集开始第一次转换": "Upload a model and dataset to start your first conversion.",
    "没有匹配的任务": "No matching tasks",
    "当前筛选下无任务，试试切换到": "No tasks match this filter. Try switching to",
    "任务": "tasks",
    "查看": "View",
    "删除": "Delete",
    "运行中任务不可删除": "Running tasks cannot be deleted",
    "任务目录和转换结果都会被删除。": "The task directory and conversion results will be deleted.",
    "删除任务": "Delete task",
    "处理中": "Processing",
    "已有任务在运行，等待完成后可再次提交": "A task is already running. Submit again after it finishes.",
    "不能为空": "Required",
    "必须是数字": "Must be a number",
    "必须是整数": "Must be an integer",
    "支持 .pt / .onnx": "Supports .pt / .onnx",
    "上传 .zip 文件": "Upload a .zip file",
    "请修正表单中的错误后再提交": "Fix the form errors before submitting.",
    "上传中": "Uploading",
    "上传完成，转换任务已创建": "Upload complete. Conversion task created.",
    "转换任务已创建": "Conversion task created.",
    "正在上传": "Uploading",
    "上传失败": "Upload failed",
    "拖拽上传文件": "Drag a file here",
    "松开上传文件": "Release to upload file",
    "语言": "Language",
  };

  const enToZh = Object.fromEntries(Object.entries(zhToEn).map(([zh, en]) => [en, zh]));
  const apiEnToZh = {
    "images_num must be between 1 and 5000": "图片数量必须在 1 到 5000 之间",
    "model must be .pt or .onnx": "模型文件必须是 .pt 或 .onnx",
    "dataset upload must be .zip": "量化数据集必须上传 .zip 文件",
    "model_name is required": "模型名称不能为空",
    "invalid result zip path": "结果 zip 路径无效",
    "result zip is not ready": "结果 zip 尚未生成",
    "cannot delete a queued or running job": "不能删除排队中或运行中的任务",
    "can only cancel queued or running jobs": "只能取消排队中或运行中的任务",
    "job was deleted": "任务已被删除",
    "job metadata not found": "找不到任务元数据",
    "invalid job_id": "任务 ID 无效",
    "job not found": "任务不存在",
  };

  const regexTranslations = [
    {
      zh: /^网络请求失败：(.+)$/,
      en: /^Network request failed: (.+)$/,
      toEn: "Network request failed: $1",
      toZh: "网络请求失败：$1",
    },
    {
      zh: /^确定取消任务 (.+)？$/,
      en: /^Cancel task (.+)\?$/,
      toEn: "Cancel task $1?",
      toZh: "确定取消任务 $1？",
    },
    {
      zh: /^删除任务 (.+)？$/,
      en: /^Delete task (.+)\?$/,
      toEn: "Delete task $1?",
      toZh: "删除任务 $1？",
    },
    {
      zh: /^任务 (.+) 已删除$/,
      en: /^Task (.+) deleted$/,
      toEn: "Task $1 deleted",
      toZh: "任务 $1 已删除",
    },
    {
      zh: /^共 (\d+) 个任务$/,
      en: /^(\d+) tasks total$/,
      toEn: "$1 tasks total",
      toZh: "共 $1 个任务",
    },
    {
      zh: /^(\d+) \/ (\d+) 个任务$/,
      en: /^(\d+) \/ (\d+) tasks$/,
      toEn: "$1 / $2 tasks",
      toZh: "$1 / $2 个任务",
    },
    {
      zh: /^加载更多（剩余 (\d+) 个）$/,
      en: /^Load more \((\d+) remaining\)$/,
      toEn: "Load more ($1 remaining)",
      toZh: "加载更多（剩余 $1 个）",
    },
    {
      zh: /^范围 ([\d.-]+)-([\d.-]+)$/,
      en: /^Range ([\d.-]+)-([\d.-]+)$/,
      toEn: "Range $1-$2",
      toZh: "范围 $1-$2",
    },
    {
      zh: /^必须是 (\d+) 的倍数$/,
      en: /^Must be a multiple of (\d+)$/,
      toEn: "Must be a multiple of $1",
      toZh: "必须是 $1 的倍数",
    },
    {
      zh: /^正在上传 (\d+)%$/,
      en: /^Uploading (\d+)%$/,
      toEn: "Uploading $1%",
      toZh: "正在上传 $1%",
    },
    {
      zh: /^上传中 (\d+)%$/,
      en: /^Uploading (\d+)%$/,
      toEn: "Uploading $1%",
      toZh: "上传中 $1%",
    },
    {
      zh: /^上传失败：(.+)$/,
      en: /^Upload failed: (.+)$/,
      toEn: "Upload failed: $1",
      toZh: "上传失败：$1",
    },
    {
      zh: /^不支持的文件类型 (.+)，仅支持 (.+)$/,
      en: /^Unsupported file type (.+). Supported: (.+)$/,
      toEn: "Unsupported file type $1. Supported: $2",
      toZh: "不支持的文件类型 $1，仅支持 $2",
    },
    {
      zh: /^不支持的目标设备：(.+)$/,
      en: /^unsupported target: (.+)$/,
      toEn: "unsupported target: $1",
      toZh: "不支持的目标设备：$1",
    },
    {
      zh: /^保存上传文件失败：(.+)$/,
      en: /^failed to save upload: (.+)$/,
      toEn: "failed to save upload: $1",
      toZh: "保存上传文件失败：$1",
    },
    {
      zh: /^转换器退出，状态码：(.+)$/,
      en: /^converter exited with code (.+)$/,
      toEn: "converter exited with code $1",
      toZh: "转换器退出，状态码：$1",
    },
    {
      zh: /^任务元数据无效：(.+)$/,
      en: /^invalid job metadata: (.+)$/,
      toEn: "invalid job metadata: $1",
      toZh: "任务元数据无效：$1",
    },
    {
      zh: /^(.+) 必须在 (\d+) 到 (\d+) 之间$/,
      en: /^(.+) must be between (\d+) and (\d+)$/,
      toEn: "$1 must be between $2 and $3",
      toZh: "$1 必须在 $2 到 $3 之间",
    },
    {
      zh: /^(.+) 必须是 (\d+) 的倍数$/,
      en: /^(.+) must be a multiple of (\d+)$/,
      toEn: "$1 must be a multiple of $2",
      toZh: "$1 必须是 $2 的倍数",
    },
  ];

  let currentLanguage = normalizeLanguage(localStorage.getItem(storageKey) || navigator.language);
  let observer = null;

  function normalizeLanguage(language) {
    if (!language) {
      return defaultLanguage;
    }
    const lowered = language.toLowerCase();
    if (lowered.startsWith("zh")) {
      return "zh-CN";
    }
    if (lowered.startsWith("en")) {
      return "en-US";
    }
    return defaultLanguage;
  }

  function translateCore(text, language) {
    if (!text) {
      return text;
    }
    if (language === "zh-CN") {
      if (apiEnToZh[text]) {
        return apiEnToZh[text];
      }
      if (enToZh[text]) {
        return enToZh[text];
      }
      for (const rule of regexTranslations) {
        if (rule.en.test(text)) {
          return text.replace(rule.en, rule.toZh);
        }
      }
      return text;
    }
    if (zhToEn[text]) {
      return zhToEn[text];
    }
    for (const rule of regexTranslations) {
      if (rule.zh.test(text)) {
        return text.replace(rule.zh, rule.toEn);
      }
    }
    return text;
  }

  function translateText(text, language) {
    const leading = text.match(/^\s*/)[0];
    const trailing = text.match(/\s*$/)[0];
    const core = text.slice(leading.length, text.length - trailing.length);
    const translated = translateCore(core, language);
    return leading + translated + trailing;
  }

  function shouldSkipTextNode(node) {
    const parent = node.parentElement;
    if (!parent) {
      return true;
    }
    return Boolean(parent.closest("script, style, noscript, textarea"));
  }

  function applyTextTranslations(root, language) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) {
      nodes.push(walker.currentNode);
    }
    for (const node of nodes) {
      if (shouldSkipTextNode(node)) {
        continue;
      }
      const next = translateText(node.nodeValue || "", language);
      if (next !== node.nodeValue) {
        node.nodeValue = next;
      }
    }
  }

  function applyAttributeTranslations(root, language) {
    if (root.nodeType !== Node.ELEMENT_NODE && root.nodeType !== Node.DOCUMENT_NODE) {
      return;
    }
    const elements = root.nodeType === Node.ELEMENT_NODE ? [root, ...root.querySelectorAll("*")] : root.querySelectorAll("*");
    for (const element of elements) {
      for (const attr of ["title", "aria-label", "data-drag-text", "placeholder"]) {
        if (!element.hasAttribute(attr)) {
          continue;
        }
        const current = element.getAttribute(attr) || "";
        const next = translateText(current, language);
        if (next !== current) {
          element.setAttribute(attr, next);
        }
      }
    }
  }

  function applyKeyedTranslations(language) {
    document.querySelectorAll("[data-i18n]").forEach((element) => {
      const key = element.getAttribute("data-i18n");
      if (!key) {
        return;
      }
      const text = key === "language.label" ? translateCore("语言", language) : translateCore(key, language);
      element.textContent = text;
    });
  }

  function applyLanguage(language) {
    currentLanguage = normalizeLanguage(language);
    localStorage.setItem(storageKey, currentLanguage);
    document.documentElement.lang = currentLanguage;
    document.documentElement.dataset.lang = currentLanguage;

    const select = document.getElementById("languageSelect");
    if (select && select.value !== currentLanguage) {
      select.value = currentLanguage;
    }

    if (observer) {
      observer.disconnect();
    }
    applyKeyedTranslations(currentLanguage);
    applyTextTranslations(document.body, currentLanguage);
    applyAttributeTranslations(document, currentLanguage);
    observeMutations();
  }

  function observeMutations() {
    observer = new MutationObserver((mutations) => {
      observer.disconnect();
      for (const mutation of mutations) {
        if (mutation.type === "characterData") {
          const node = mutation.target;
          if (!shouldSkipTextNode(node)) {
            const next = translateText(node.nodeValue || "", currentLanguage);
            if (next !== node.nodeValue) {
              node.nodeValue = next;
            }
          }
          continue;
        }
        if (mutation.type === "childList") {
          mutation.addedNodes.forEach((node) => {
            if (node.nodeType === Node.TEXT_NODE) {
              if (!shouldSkipTextNode(node)) {
                const next = translateText(node.nodeValue || "", currentLanguage);
                if (next !== node.nodeValue) {
                  node.nodeValue = next;
                }
              }
              return;
            }
            if (node.nodeType === Node.ELEMENT_NODE) {
              applyTextTranslations(node, currentLanguage);
              applyAttributeTranslations(node, currentLanguage);
            }
          });
        }
        if (mutation.type === "attributes" && mutation.target.nodeType === Node.ELEMENT_NODE) {
          applyAttributeTranslations(mutation.target, currentLanguage);
        }
      }
      observeMutations();
    });
    observer.observe(document.body, {
      attributes: true,
      attributeFilter: ["title", "aria-label", "data-drag-text", "placeholder"],
      childList: true,
      characterData: true,
      subtree: true,
    });
  }

  function setupLanguageSelect() {
    const select = document.getElementById("languageSelect");
    if (!select) {
      return;
    }
    select.innerHTML = "";
    Object.entries(languages).forEach(([value, label]) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      select.appendChild(option);
    });
    select.value = currentLanguage;
    select.addEventListener("change", () => applyLanguage(select.value));
  }

  function init() {
    setupLanguageSelect();
    applyLanguage(currentLanguage);
  }

  window.MaixI18n = {
    getLanguage: () => currentLanguage,
    setLanguage: applyLanguage,
    t: (text) => translateCore(text, currentLanguage),
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
