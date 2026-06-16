import type { CognitiveOutput } from "./cognitiveTypes";

/** Demo 模式 — 各层内容刻意区分，避免重复感 */
export const DEMO_COGNITIVE_OUTPUT: CognitiveOutput = {
  summary: [
    {
      text: "过去 120 条事件中：embed×18、chat×12、system×3；出现 2 次 502 与 1 次降级。",
      confidence: 0.9,
      source: "exec_log",
    },
    {
      text: "对话链路稳定，无并发排队；治理状态为 observe。",
      confidence: 0.91,
      source: "scheduler",
    },
  ],
  patterns: [
    {
      text: "高峰时段 embed 与 chat 同时触发时，延迟上升约 2×。",
      confidence: 0.76,
      source: "pattern",
    },
    {
      text: "Embedding 缓存命中率 80%（命中 8 / 未命中 2）。",
      confidence: 0.9,
      source: "scheduler_cache",
    },
  ],
  rules: [
    {
      text: "本地 16GB 内存下，单并发 + embed/chat 互斥是稳妥默认。",
      confidence: 0.88,
      source: "policy",
    },
  ],
  experiences: [
    {
      text: "16GB 机器上优先单并发，embed 与 chat 互斥更稳。",
      confidence: 0.88,
      source: "experience:policy",
    },
    {
      text: "高峰时段避免 embed 与 chat 并发，可显著降低延迟波动。",
      confidence: 0.8,
      source: "experience:pattern",
    },
  ],
  insights: [
    {
      title: "向量路径存在结构性风险",
      description: "Ollama embed 间歇失败，系统已走 hash 降级，召回质量可能下降。",
      confidence: 0.85,
      why: "502 连续出现在 embed 调用链，且降级后未自动恢复",
      source: "embed_path",
      novelty: 0.55,
      evidence: ["Ollama embed 失败，已降级 hash 向量", "检测到 Ollama 502，等待重试"],
    },
    {
      title: "算力余量仍充足",
      description: "chat 负载低，具备恢复语义 embed 或提高并发的空间。",
      confidence: 0.72,
      why: "近窗口无 chat 排队，scheduler 单车道未饱和",
      source: "compute",
      novelty: 0.35,
      evidence: ["对话完成 · 1.2s · qwen2.5:7b"],
    },
  ],
  discoveries: [
    {
      id: "demo-disc-1",
      title: "新规律：高峰 embed+chat 叠加",
      description: "高峰时段 embed 与 chat 同时触发时，延迟上升约 2×。",
      confidence: 0.76,
      novelty: 0.88,
      why: "与上一观察窗口对比，该叠加效应首次被量化识别。",
      evidence: ["对话完成 · 1.2s · qwen2.5:7b", "Ollama embed 失败，已降级 hash 向量"],
      source: "novel_pattern:pattern",
      first_seen_at: new Date().toISOString(),
    },
    {
      id: "demo-disc-2",
      title: "相较上周期新出现：向量路径存在结构性风险",
      description: "502 连续出现在 embed 调用链，且降级后未自动恢复",
      confidence: 0.85,
      novelty: 0.82,
      why: "与历史合成快照对比，该信号此前未出现或显著增强。",
      evidence: ["检测到 Ollama 502，等待重试"],
      source: "novel_signal:embed_path",
      first_seen_at: new Date().toISOString(),
    },
  ],
  narrative:
    "过去 120 条事件中：embed×18、chat×12、system×3；出现 2 次 502 与 1 次降级。对话链路稳定，无并发排队；治理状态为 observe。解读：向量路径存在结构性风险——502 连续出现在 embed 调用链，且降级后未自动恢复。新变化：高峰时段 embed 与 chat 同时触发时，延迟上升约 2×。建议：减少重复 embed 计算。",
  actions: [
    {
      action: "enable_aggressive_embed_cache",
      priority: 0.9,
      rationale: "减少重复 embed 计算",
      category: "scheduler",
      impact: 0.8,
      reversibility: 0.95,
      why: "日志显示相同文本被多次 embed",
    },
    {
      action: "restore_ollama_embedding",
      priority: 0.65,
      rationale: "提升记忆召回质量",
      category: "model",
      impact: 0.7,
      reversibility: 0.9,
      why: "Ollama 已恢复在线",
    },
  ],
  top_actions: [
    {
      action: "enable_aggressive_embed_cache",
      priority: 0.9,
      rationale: "减少重复 embed 计算",
      category: "scheduler",
      impact: 0.8,
      reversibility: 0.95,
      why: "日志显示相同文本被多次 embed",
    },
  ],
  generated_at: new Date().toISOString(),
  window_size: 120,
  mode: "demo",
};

export const DEMO_EXEC_LOGS = [
  {
    id: "demo-ir-1",
    timestamp: new Date().toISOString(),
    level: "info",
    category: "ir",
    message: "IR compile",
    meta: { node_count: 12, graph_id: "g-demo", template: "chat_single_turn" },
  },
  {
    id: "demo-exec-1",
    timestamp: new Date(Date.now() - 15_000).toISOString(),
    level: "info",
    category: "chat",
    message: "Prepare outbound payload",
  },
  {
    id: "demo-mem-1",
    timestamp: new Date(Date.now() - 30_000).toISOString(),
    level: "debug",
    category: "recall",
    message: "Recall query",
    meta: { chars: 420, query: "embed latency" },
  },
  {
    id: "demo-mem-2",
    timestamp: new Date(Date.now() - 45_000).toISOString(),
    level: "info",
    category: "capture",
    message: "Memory captured",
    meta: { layer: "episodic", id: "mem-demo-001" },
  },
  {
    id: "demo-cse-1",
    timestamp: new Date(Date.now() - 60_000).toISOString(),
    level: "info",
    category: "cse",
    message: "Synthesize requested",
    meta: { window: 120 },
  },
  {
    id: "demo-gov-1",
    timestamp: new Date(Date.now() - 90_000).toISOString(),
    level: "info",
    category: "governance",
    message: "Cycle complete",
    meta: { stability: 0.91 },
  },
  {
    id: "demo-embed-1",
    timestamp: new Date(Date.now() - 120_000).toISOString(),
    level: "info",
    category: "embed",
    message: "Ollama embed 失败，已降级 hash 向量",
  },
  {
    id: "demo-sys-1",
    timestamp: new Date(Date.now() - 150_000).toISOString(),
    level: "warn",
    category: "system",
    message: "检测到 Ollama 502，等待重试",
  },
];
