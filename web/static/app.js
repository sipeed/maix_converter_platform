const form = document.querySelector("#jobForm");
const modelFile = document.querySelector("#modelFile");
const datasetFile = document.querySelector("#datasetFile");
const modelFileName = document.querySelector("#modelFileName");
const datasetFileName = document.querySelector("#datasetFileName");
const modelName = document.querySelector("#modelName");
const submitButton = document.querySelector("#submitButton");
const serverState = document.querySelector("#serverState");
const jobStatus = document.querySelector("#jobStatus");
const jobId = document.querySelector("#jobId");
const jobModel = document.querySelector("#jobModel");
const jobDone = document.querySelector("#jobDone");
const logView = document.querySelector("#logView");
const refreshButton = document.querySelector("#refreshButton");
const downloadButton = document.querySelector("#downloadButton");
const jobsList = document.querySelector("#jobsList");
const reloadJobs = document.querySelector("#reloadJobs");
const uploadProgress = document.querySelector("#uploadProgress");
const uploadProgressBar = document.querySelector("#uploadProgressBar");
const uploadProgressText = document.querySelector("#uploadProgressText");

let activeJobId = "";
let streamSocket = null;
let currentLog = "";

modelFile.addEventListener("change", () => {
  updateFileName(modelFile, modelFileName, "支持 .pt / .onnx");
  if (modelName.value.trim() || !modelFile.files.length) return;
  const name = modelFile.files[0].name.replace(/\.[^.]+$/, "");
  modelName.value = name.replace(/[^A-Za-z0-9_.-]+/g, "_");
});

datasetFile.addEventListener("change", () => {
  updateFileName(datasetFile, datasetFileName, "上传 .zip 文件");
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  submitButton.disabled = true;
  submitButton.textContent = "上传中";
  resetProgress();
  setStatus("queued");
  currentLog = "";
  logView.textContent = "正在上传文件...";

  try {
    const data = await uploadJob(new FormData(form));
    setProgress(100, "上传完成，转换任务已创建");
    hideProgressSoon();
    setActiveJob(data.job_id);
    await refreshJobsList();
  } catch (error) {
    logView.textContent = String(error);
    setStatus("failed");
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "开始转换";
  }
});

refreshButton.addEventListener("click", () => {
  if (activeJobId) refreshJob();
});

reloadJobs.addEventListener("click", refreshJobsList);

async function checkHealth() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) throw new Error("bad health");
    serverState.textContent = "API 在线";
    serverState.classList.add("ok");
  } catch {
    serverState.textContent = "API 离线";
    serverState.classList.remove("ok");
  }
}

function uploadJob(body) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/jobs");

    xhr.upload.addEventListener("progress", (event) => {
      if (!event.lengthComputable) {
        uploadProgressText.textContent = "正在上传";
        return;
      }
      const percent = Math.max(1, Math.round((event.loaded / event.total) * 100));
      setProgress(percent, `正在上传 ${percent}%`);
    });

    xhr.addEventListener("load", () => {
      if (xhr.status < 200 || xhr.status >= 300) {
        reject(new Error(xhr.responseText || `HTTP ${xhr.status}`));
        return;
      }
      try {
        resolve(JSON.parse(xhr.responseText));
      } catch (error) {
        reject(error);
      }
    });

    xhr.addEventListener("error", () => reject(new Error("上传失败")));
    xhr.addEventListener("abort", () => reject(new Error("上传已取消")));
    xhr.send(body);
  });
}

function setActiveJob(id) {
  activeJobId = id;
  currentLog = "";
  jobId.textContent = id;
  downloadButton.href = "#";
  downloadButton.classList.add("disabled");
  downloadButton.classList.remove("ready");
  downloadButton.setAttribute("aria-disabled", "true");
  openLogStream(id);
}

function openLogStream(id) {
  if (streamSocket) streamSocket.close();

  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  streamSocket = new WebSocket(`${protocol}://${window.location.host}/api/jobs/${id}/stream`);

  streamSocket.addEventListener("open", () => {
    appendLog("日志连接已建立\n");
  });

  streamSocket.addEventListener("message", (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "job") {
      renderJob(data.job);
    } else if (data.type === "log") {
      appendLog(data.text);
    } else if (data.type === "error") {
      appendLog(`${data.message}\n`);
      setStatus("failed");
    }
  });

  streamSocket.addEventListener("close", () => {
    refreshJob();
    refreshJobsList();
  });
}

async function refreshJob() {
  if (!activeJobId) return;
  const response = await fetch(`/api/jobs/${activeJobId}`);
  if (!response.ok) {
    appendLog(await response.text());
    setStatus("failed");
    return;
  }

  const job = await response.json();
  renderJob(job);
}

function appendLog(text) {
  currentLog += text;
  if (currentLog.length > 180000) {
    currentLog = currentLog.slice(currentLog.length - 160000);
  }
  logView.textContent = currentLog || "暂无日志";
  logView.scrollTop = logView.scrollHeight;
}

function renderJob(job) {
  setStatus(job.status || "unknown");
  jobId.textContent = job.job_id || activeJobId || "-";
  jobModel.textContent = job.model_name || "-";
  jobDone.textContent = job.completed_at || "-";

  if (job.status === "success") {
    downloadButton.href = `/api/jobs/${job.job_id || activeJobId}/download`;
    downloadButton.classList.remove("disabled");
    downloadButton.classList.add("ready");
    downloadButton.removeAttribute("aria-disabled");
  } else {
    downloadButton.classList.remove("ready");
  }
}

function setStatus(status) {
  jobStatus.textContent = statusText(status);
  jobStatus.className = `status-badge ${status || "idle"}`;
}

function statusText(status) {
  const names = {
    queued: "排队中",
    running: "转换中",
    success: "已完成",
    failed: "失败",
    unknown: "未知",
    idle: "未开始",
  };
  return names[status] || status || "未开始";
}

async function refreshJobsList() {
  const response = await fetch("/api/jobs");
  if (!response.ok) return;
  const data = await response.json();
  jobsList.innerHTML = "";

  for (const job of data.jobs.slice(0, 8)) {
    const row = document.createElement("div");
    row.className = "job-row";

    const id = document.createElement("div");
    id.className = "job-id";
    id.textContent = job.job_id;

    const status = document.createElement("div");
    status.className = `status-badge ${job.status || "unknown"}`;
    status.textContent = statusText(job.status);

    const time = document.createElement("div");
    time.className = "muted";
    time.textContent = job.completed_at || job.created_at || "-";

    const button = document.createElement("button");
    button.className = "secondary-button";
    button.type = "button";
    button.textContent = "查看";
    button.addEventListener("click", () => {
      setActiveJob(job.job_id);
      refreshJob();
    });

    row.append(id, status, time, button);
    jobsList.append(row);
  }

  if (!data.jobs.length) {
    jobsList.innerHTML = '<div class="muted">暂无任务</div>';
  }
}

function updateFileName(input, target, fallback) {
  target.textContent = input.files.length ? input.files[0].name : fallback;
}

function resetProgress() {
  uploadProgress.classList.add("active");
  uploadProgressText.classList.add("active");
  setProgress(0, "等待上传");
}

function setProgress(percent, text) {
  uploadProgressBar.style.width = `${percent}%`;
  uploadProgressText.textContent = text;
}

function hideProgressSoon() {
  setTimeout(() => {
    uploadProgress.classList.remove("active");
    uploadProgressText.classList.remove("active");
    uploadProgressBar.style.width = "0";
    uploadProgressText.textContent = "等待上传";
  }, 900);
}

checkHealth();
refreshJobsList();
