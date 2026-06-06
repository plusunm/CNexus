const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const PROVIDER_DEFAULTS = {
  ollama: { base_url: "http://localhost:11434", model: "llama3.2" },
  openai: { base_url: "https://api.openai.com/v1", model: "gpt-4o-mini" },
  openai_compatible: { base_url: "https://api.deepseek.com/v1", model: "deepseek-chat" },
};

const PRESET_MAP = {
  deepseek: { name: "DeepSeek Chat", provider: "openai_compatible", base_url: "https://api.deepseek.com/v1", model: "deepseek-chat" },
  moonshot: { name: "Moonshot Kimi", provider: "openai_compatible", base_url: "https://api.moonshot.cn/v1", model: "moonshot-v1-8k" },
  qwen: { name: "通义千问 Qwen", provider: "openai_compatible", base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1", model: "qwen-turbo" },
  zhipu: { name: "智谱 GLM-4", provider: "openai_compatible", base_url: "https://open.bigmodel.cn/api/paas/v4", model: "glm-4-flash" },
  siliconflow: { name: "SiliconFlow DeepSeek", provider: "openai_compatible", base_url: "https://api.siliconflow.cn/v1", model: "deepseek-ai/DeepSeek-V3" },
  gemini: { name: "Google Gemini", provider: "openai_compatible", base_url: "https://generativelanguage.googleapis.com/v1beta/openai", model: "gemini-2.0-flash" },
  openai: { name: "OpenAI GPT-4o mini", provider: "openai", base_url: "https://api.openai.com/v1", model: "gpt-4o-mini" },
  ollama: { name: "Ollama 本地", provider: "ollama", base_url: "http://localhost:11434", model: "llama3.2" },
};

let models = [];

function toast(msg, type = "") {
  const el = $("#toast");
  el.textContent = msg;
  el.className = `toast ${type}`;
  setTimeout(() => el.classList.add("hidden"), 3200);
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

function switchTab(name) {
  $$(".nav-btn").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
  $$(".tab").forEach((t) => t.classList.toggle("active", t.id === `tab-${name}`));
}

function renderModelSelect() {
  const sel = $("#model-select");
  sel.innerHTML = "";
  models.filter((m) => m.enabled).forEach((m) => {
    const opt = document.createElement("option");
    opt.value = m.id;
    opt.textContent = `${m.name} (${m.model})${m.is_default ? " ★" : ""}`;
    if (m.is_default) opt.selected = true;
    sel.appendChild(opt);
  });
}

function renderModelsList() {
  const list = $("#models-list");
  list.innerHTML = "";
  if (!models.length) {
    list.innerHTML = '<p style="color:var(--muted);font-size:0.85rem">暂无模型，请右侧添加</p>';
    return;
  }
  models.forEach((m) => {
    const div = document.createElement("div");
    div.className = `model-item${m.is_default ? " default" : ""}`;
    div.innerHTML = `
      <div class="model-info">
        <h4>${m.name}${m.is_default ? " ★ 默认" : ""}</h4>
        <p>${m.provider} · ${m.model}<br/>${m.base_url} · Key: ${m.api_key_set ? "已设置" : "未设置"}</p>
      </div>
      <div class="model-actions">
        <button class="ghost-btn" data-action="test" data-id="${m.id}">测试</button>
        <button class="ghost-btn" data-action="edit" data-id="${m.id}">编辑</button>
        <button class="ghost-btn" data-action="delete" data-id="${m.id}">删除</button>
      </div>`;
    list.appendChild(div);
  });

  list.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => handleModelAction(btn.dataset.action, btn.dataset.id));
  });
}

async function loadModels() {
  const data = await api("/api/models");
  models = data.models;
  renderModelSelect();
  renderModelsList();
}

async function handleModelAction(action, id) {
  if (action === "edit") {
    const m = models.find((x) => x.id === id);
    if (!m) return;
    $("#form-title").textContent = "编辑模型";
    $("#edit-model-id").value = id;
    $("#model-name").value = m.name;
    $("#model-provider").value = m.provider;
    $("#model-base-url").value = m.base_url;
    $("#model-id-field").value = m.model;
    $("#model-api-key").value = "";
    $("#model-default").checked = m.is_default;
    switchTab("models");
    return;
  }
  if (action === "delete") {
    if (!confirm("确认删除此模型？")) return;
    await api(`/api/models/${id}`, { method: "DELETE" });
    toast("已删除", "success");
    await loadModels();
    return;
  }
  if (action === "test") {
    toast("正在测试连接…");
    try {
      const res = await api(`/api/models/${id}/test`, { method: "POST" });
      toast(res.success ? `连接成功: ${res.detail.slice(0, 60)}` : `失败: ${res.detail}`, res.success ? "success" : "error");
    } catch (e) {
      toast(e.message, "error");
    }
  }
}

function resetModelForm() {
  $("#form-title").textContent = "添加模型";
  $("#edit-model-id").value = "";
  $("#model-form").reset();
  $("#model-provider").value = "openai_compatible";
  applyProviderDefaults();
}

function applyProviderDefaults() {
  const p = $("#model-provider").value;
  const d = PROVIDER_DEFAULTS[p];
  if (d) {
    $("#model-base-url").value = d.base_url;
    $("#model-id-field").value = d.model;
  }
}

function appendMessage(role, content, meta = "") {
  const box = $("#chat-messages");
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.innerHTML = `${escapeHtml(content)}${meta ? `<div class="msg-meta">${meta}</div>` : ""}`;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function escapeHtml(text) {
  const d = document.createElement("div");
  d.textContent = text;
  return d.innerHTML;
}

async function sendChat(message) {
  const modelId = $("#model-select").value;
  const useMemory = $("#use-memory").checked;
  appendMessage("user", message);
  $("#send-btn").disabled = true;

  try {
    const data = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        message,
        model_id: modelId || undefined,
        use_memory: useMemory,
      }),
    });
    const meta = `${data.model_name}${data.memory_context_used ? " · 记忆已启用" : ""}`;
    appendMessage("assistant", data.reply, meta);
  } catch (e) {
    appendMessage("system", `错误: ${e.message}`);
    toast(e.message, "error");
  } finally {
    $("#send-btn").disabled = false;
  }
}

async function checkHealth() {
  try {
    await api("/api/health");
    $("#status-dot").classList.add("online");
  } catch {
    $("#status-dot").classList.remove("online");
    toast("后端未启动，请先运行 python scripts/run_ui.py", "error");
  }
}

// Events
$$(".nav-btn").forEach((btn) => {
  btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

$("#model-provider").addEventListener("change", applyProviderDefaults);

$("#model-preset").addEventListener("change", (e) => {
  const preset = PRESET_MAP[e.target.value];
  if (!preset) return;
  $("#model-name").value = preset.name;
  $("#model-provider").value = preset.provider;
  $("#model-base-url").value = preset.base_url;
  $("#model-id-field").value = preset.model;
});

$("#model-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const editId = $("#edit-model-id").value;
  const payload = {
    name: $("#model-name").value.trim(),
    provider: $("#model-provider").value,
    base_url: $("#model-base-url").value.trim(),
    model: $("#model-id-field").value.trim(),
    is_default: $("#model-default").checked,
  };
  const key = $("#model-api-key").value.trim();
  if (key) payload.api_key = key;

  try {
    if (editId) {
      await api(`/api/models/${editId}`, { method: "PUT", body: JSON.stringify(payload) });
      toast("模型已更新", "success");
    } else {
      await api("/api/models", { method: "POST", body: JSON.stringify(payload) });
      toast("模型已添加", "success");
    }
    resetModelForm();
    await loadModels();
  } catch (err) {
    toast(err.message, "error");
  }
});

$("#reset-form-btn").addEventListener("click", resetModelForm);

$("#chat-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = $("#chat-input");
  const msg = input.value.trim();
  if (!msg) return;
  input.value = "";
  await sendChat(msg);
});

$("#chat-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    $("#chat-form").requestSubmit();
  }
});

$("#governance-btn").addEventListener("click", async () => {
  try {
    const data = await api("/api/governance", { method: "POST" });
    const score = data.stability_metrics?.overall_stability_score?.toFixed(3) ?? "N/A";
    toast(`治理完成 · 稳定性 ${score}`, "success");
  } catch (e) {
    toast(e.message, "error");
  }
});

// Init
resetModelForm();
checkHealth();
loadModels().catch(() => {});
appendMessage("system", "Brain-Memory G1 已就绪。在「模型配置」中添加 API，然后开始对话。");
