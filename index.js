import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PID_FILE = path.join(__dirname, ".brain-memory-rpc.pid");

const PYTHON_CANDIDATES = [
  process.env.BRAIN_MEMORY_PYTHON,
  "C:\\Python311\\python.exe",
  "C:\\Program Files\\Python312\\python.exe",
  "C:\\Program Files\\Python311\\python.exe",
].filter(Boolean);

function resolvePythonExecutable(config) {
  const fromConfig = config?.python_executable || config?.pythonExecutable;
  if (fromConfig && fs.existsSync(fromConfig)) return fromConfig;
  for (const candidate of PYTHON_CANDIDATES) {
    if (candidate && fs.existsSync(candidate)) return candidate;
  }
  return process.env.BRAIN_MEMORY_PYTHON || "C:\\Python311\\python.exe";
}

class BrainMemoryRpc {
  constructor(pluginDir, config, logger) {
    this.pluginDir = pluginDir;
    this.config = config ?? {};
    this.logger = logger;
    this.proc = null;
    this.pending = new Map();
    this.nextId = 1;
    this.buffer = "";
    this.startPromise = null;
  }

  async start() {
    if (this.proc) return;
    if (this.startPromise) return this.startPromise;

    this.startPromise = this.#spawnServer();

    try {
      await this.startPromise;
    } finally {
      this.startPromise = null;
    }
  }

  #spawnServer() {
    return new Promise((resolve, reject) => {
      const python = resolvePythonExecutable(this.config);
      const script = path.join(this.pluginDir, "rpc_server.py");
      if (!fs.existsSync(python)) {
        reject(new Error(`brain-memory: python not found (${python})`));
        return;
      }

      this.proc = spawn(python, [script], {
        cwd: this.pluginDir,
        stdio: ["pipe", "pipe", "pipe"],
        env: {
          ...process.env,
          BRAIN_MEMORY_CONFIG: JSON.stringify(this.config),
          BRAIN_MEMORY_QUIET: "1",
          OLLAMA_MODELS: process.env.OLLAMA_MODELS || "D:\\ollama_models",
        },
      });

      this.proc.on("error", (err) => {
        this.proc = null;
        reject(new Error(`brain-memory: failed to start python rpc (${python}): ${err.message}`));
      });

      this.proc.stdout.on("data", (chunk) => {
        this.buffer += chunk.toString("utf8");
        let idx;
        while ((idx = this.buffer.indexOf("\n")) >= 0) {
          const line = this.buffer.slice(0, idx).trim();
          this.buffer = this.buffer.slice(idx + 1);
          if (!line) continue;
          try {
            const msg = JSON.parse(line);
            const waiter = this.pending.get(msg.id);
            if (!waiter) continue;
            this.pending.delete(msg.id);
            clearTimeout(waiter.timer);
            if (msg.ok) waiter.resolve(msg.result);
            else waiter.reject(new Error(msg.error || "rpc error"));
          } catch (err) {
            this.logger?.warn?.(`brain-memory: bad rpc line: ${String(err)}`);
          }
        }
      });

      this.proc.stderr.on("data", (chunk) => {
        const text = chunk.toString("utf8").trim();
        if (text) this.logger?.warn?.(`brain-memory: ${text}`);
      });

      this.proc.on("exit", (code) => {
        this.logger?.warn?.(`brain-memory rpc exited (${code})`);
        this.proc = null;
        try {
          if (fs.existsSync(PID_FILE)) fs.unlinkSync(PID_FILE);
        } catch {}
        for (const [, waiter] of this.pending) {
          clearTimeout(waiter.timer);
          waiter.reject(new Error("brain-memory rpc process exited"));
        }
        this.pending.clear();
      });

      if (this.proc.pid) {
        try {
          fs.writeFileSync(PID_FILE, String(this.proc.pid));
        } catch {}
      }

      const pingId = this.nextId++;
      const pingPayload = JSON.stringify({ id: pingId, method: "ping", params: {} }) + "\n";
      const pingTimer = setTimeout(() => {
        this.pending.delete(pingId);
        reject(new Error("brain-memory rpc warmup timeout"));
      }, 120000);

      this.pending.set(pingId, {
        resolve: () => {
          clearTimeout(pingTimer);
          resolve();
        },
        reject: (err) => {
          clearTimeout(pingTimer);
          reject(err);
        },
        timer: pingTimer,
      });

      this.proc.stdin?.write(pingPayload, (err) => {
        if (err) {
          clearTimeout(pingTimer);
          this.pending.delete(pingId);
          reject(err);
        }
      });
    });
  }

  stop() {
    if (!this.proc) return;
    this.proc.kill();
    this.proc = null;
    try {
      if (fs.existsSync(PID_FILE)) fs.unlinkSync(PID_FILE);
    } catch {}
  }

  async call(method, params = {}, timeoutMs = 180000) {
    await this.start();
    if (!this.proc?.stdin) throw new Error("brain-memory rpc not running");

    const id = this.nextId++;
    const payload = JSON.stringify({ id, method, params }) + "\n";

    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`brain-memory rpc timeout: ${method}`));
      }, timeoutMs);

      this.pending.set(id, { resolve, reject, timer });
      this.proc.stdin.write(payload, (err) => {
        if (err) {
          clearTimeout(timer);
          this.pending.delete(id);
          reject(err);
        }
      });
    });
  }
}

function formatRecallContext(detail) {
  if (!detail?.context) return null;
  const prov = detail.provenance ? `\n<!-- provenance: ${JSON.stringify(detail.provenance)} -->` : "";
  return `<brain-memory-recall>\n${detail.context}${prov}\n</brain-memory-recall>`;
}

function extractUserTexts(messages) {
  const texts = [];
  for (const msg of messages ?? []) {
    if (!msg || typeof msg !== "object") continue;
    if (msg.role !== "user") continue;
    const content = msg.content;
    if (typeof content === "string") {
      if (content.trim()) texts.push(content.trim());
      continue;
    }
    if (Array.isArray(content)) {
      for (const block of content) {
        if (block?.type === "text" && typeof block.text === "string" && block.text.trim()) {
          texts.push(block.text.trim());
        }
      }
    }
  }
  return texts;
}

export default {
  id: "brain-memory",
  name: "Brain Memory",
  description: "Cognitive Stability v5.0 — Deterministic Router + Belief System + Reflection + Goal Lifecycle",
  kind: "memory",
  configSchema: {
    type: "object",
    additionalProperties: false,
    properties: {
      ollama_host: { type: "string" },
      embedding_model: { type: "string" },
      llm_model: { type: "string" },
      embedding_dim: { type: "number" },
      auto_capture: { type: "boolean" },
      auto_recall: { type: "boolean" },
      use_hyde: { type: "boolean" },
      recall_top_k: { type: "number" },
      consolidate_enabled: { type: "boolean" },
      scheduler_enabled: { type: "boolean" },
      importance_threshold: { type: "number" },
      min_capture_len: { type: "number" },
      enable_multi_hop: { type: "boolean" },
      enable_metabolic: { type: "boolean" },
      dedup_similarity: { type: "number" },
      forget_alpha: { type: "number" },
      hebbian_strength: { type: "number" },
      reconsolidate_enabled: { type: "boolean" },
      short_term_capacity: { type: "number" },
      write_gate_threshold: { type: "number" },
      graph_prune_confidence: { type: "number" },
      compress_similarity: { type: "number" },
      attention_half_life: { type: "number" },
      belief_compat_threshold: { type: "number" },
      reflection_enabled: { type: "boolean" },
      agent_identity: { type: "string" },
    },
  },
  register(api) {
    const cfg = {
      ollama_host: "http://localhost:11434",
      embedding_model: "nomic-embed-text",
      llm_model: "llama3.2:3b",
      auto_capture: true,
      auto_recall: true,
      use_hyde: true,
      recall_top_k: 12,
      enable_multi_hop: true,
      enable_metabolic: true,
      ...api.pluginConfig,
    };

    const rpc = new BrainMemoryRpc(__dirname, cfg, api.logger);

    api.registerMemoryPromptSection(({ availableTools }) => {
      const names = ["brain_recall", "brain_store", "brain_consolidate"];
      const has = names.some((n) => availableTools.has(n));
      if (!has) return [];
      return [
        "## Brain Memory",
        "Long-term local memory via brain_recall / brain_store. Prefer brain_recall before answering about past work, preferences, or decisions.",
        "",
      ];
    });

    const tool = (name, description, execute) => {
      api.registerTool({
        name,
        label: name,
        description,
        parameters: { type: "object", properties: {} },
        async execute(_id, params) {
          const out = await execute(params);
          const text = typeof out === "string" ? out : JSON.stringify(out, null, 2);
          return { content: [{ type: "text", text }] };
        },
      }, { name });
    };

    tool("brain_recall", "HyDE hybrid memory recall", async (p) =>
      rpc.call("recall", { query: p.query ?? "", top_k: p.top_k, use_hyde: p.use_hyde ?? cfg.use_hyde }));

    tool("brain_store", "Store episodic/semantic memory", async (p) =>
      rpc.call("capture", {
        role: p.role ?? "assistant",
        content: p.content ?? "",
        layer: p.layer ?? "episodic",
        session_id: p.session_id ?? "default",
      }));

    tool("brain_consolidate", "Run sleep consolidation to semantic summaries", async () =>
      rpc.call("consolidate"));

    tool("brain_stats", "Brain memory statistics", async () => rpc.call("stats"));

    tool(
      "brain_link_provenance",
      "Link agent answer to cited memory nodes (SUPPORTED_BY graph)",
      async (p) =>
        rpc.call("link_provenance", {
          query: p.query ?? "",
          answer: p.answer ?? "",
          cited_ids: p.cited_ids ?? [],
        }),
    );

    if (cfg.auto_recall !== false) {
      api.on("before_agent_start", async (event) => {
        const prompt = event.prompt?.trim();
        if (!prompt || prompt.length < 5) return;
        try {
          const detail = await rpc.call("recall_detail", {
            query: prompt,
            top_k: cfg.recall_top_k,
            use_hyde: cfg.use_hyde,
          });
          const prependContext = formatRecallContext(detail);
          if (prependContext) {
            api.logger.info?.("brain-memory: injecting recall context");
            return { prependContext };
          }
        } catch (err) {
          api.logger.warn?.(`brain-memory: auto-recall failed: ${String(err)}`);
        }
      });
    }

    if (cfg.auto_capture !== false) {
      api.on("agent_end", async (event) => {
        if (!event.success || !event.messages?.length) return;
        const minLen = cfg.min_capture_len ?? 8;
        const texts = extractUserTexts(event.messages).filter((t) => t.length >= minLen);
        for (const text of texts.slice(0, 3)) {
          try {
            await rpc.call("capture", { role: "user", content: text, layer: "episodic" });
          } catch (err) {
            api.logger.warn?.(`brain-memory: auto-capture failed: ${String(err)}`);
          }
        }
      });
    }

    api.registerService({
      id: "brain-memory-rpc",
      start: async () => {
        try {
          const stats = await rpc.call("ping");
          api.logger.info?.(`brain-memory: ready (${stats?.total_memories ?? "?"} memories)`);
        } catch (err) {
          api.logger.error?.(`brain-memory: rpc start failed: ${String(err)}`);
        }
      },
      stop: () => rpc.stop(),
    });
  },
};
