/**
 * CNexus v1 core contracts — CSE / Σ_exec / Config Surface
 */

export type ExecEvent = {
  id: string;
  type: "chat" | "embed" | "memory" | "system";
  latency: number;
  model: string;
  timestamp: number;
  metadata?: Record<string, unknown>;
};

export type CognitiveTextBlock = {
  text: string;
  confidence: number;
  source: string;
};

export type CognitiveInsightBlock = {
  title: string;
  description: string;
  confidence: number;
  why: string;
  source: string;
  novelty?: number;
  evidence?: string[];
};

export type CognitiveDiscoveryBlock = {
  id: string;
  title: string;
  description: string;
  confidence: number;
  novelty: number;
  why: string;
  evidence: string[];
  source: string;
  first_seen_at?: string;
};

export type CognitiveActionBlock = {
  action: string;
  priority: number;
  rationale: string;
  category: string;
  impact: number;
  reversibility: number;
  why: string;
};

export type CognitiveOutput = {
  summary: CognitiveTextBlock[];
  patterns: CognitiveTextBlock[];
  insights: CognitiveInsightBlock[];
  rules: CognitiveTextBlock[];
  experiences: CognitiveTextBlock[];
  discoveries: CognitiveDiscoveryBlock[];
  actions: CognitiveActionBlock[];
  narrative?: string;
  top_actions?: CognitiveActionBlock[];
  generated_at: string;
  window_size: number;
  mode: string;
  exec_traces?: ExecTraceManifest[];
};

export type ExecTraceManifest = {
  trace_id: string;
  graph_id?: string;
  template_name?: string;
  status?: string;
};

export type ExecLogEvent = {
  id: string;
  timestamp: string;
  level: string;
  category: string;
  message: string;
  meta?: Record<string, unknown>;
};

export type CNexusConfig = {
  system: { mode: "local" | "hybrid" | "cloud"; debug_trace: boolean };
  model: { llm_provider: string; chat_model: string; embedding_model: string };
  scheduler: { max_concurrency: number; embed_chat_mutex: boolean };
  cse: { enabled: boolean; window_size: number; auto_synthesize: boolean };
  governance: { strict_mode: boolean; allow_runtime_mutation: boolean };
};

export type ConfigPresetId = "balanced" | "performance" | "safe" | "cognitive" | "debug";

export const CONFIG_PRESETS: Record<
  ConfigPresetId,
  { label: string; description: string; patch: Partial<CNexusConfig> }
> = {
  balanced: {
    label: "均衡模式",
    description: "日常推荐 — 稳定与响应速度兼顾",
    patch: {
      scheduler: { max_concurrency: 1, embed_chat_mutex: true },
      cse: { enabled: true, window_size: 120, auto_synthesize: true },
    },
  },
  performance: {
    label: "高性能",
    description: "机器资源充足时 — 更高并发",
    patch: {
      scheduler: { max_concurrency: 2, embed_chat_mutex: false },
      cse: { enabled: true, window_size: 200, auto_synthesize: true },
    },
  },
  safe: {
    label: "稳妥模式",
    description: "内存紧张时 — 单任务优先",
    patch: {
      scheduler: { max_concurrency: 1, embed_chat_mutex: true },
      cse: { enabled: true, window_size: 100, auto_synthesize: true },
    },
  },
  cognitive: {
    label: "深度分析",
    description: "更长观察窗口 — 结论更细",
    patch: {
      cse: { enabled: true, window_size: 300, auto_synthesize: true },
    },
  },
  debug: {
    label: "调试追踪",
    description: "开发者 — 完整运行轨迹",
    patch: {
      system: { mode: "local", debug_trace: true },
      cse: { enabled: true, window_size: 500, auto_synthesize: false },
    },
  },
};

export type IntentMode = "ask" | "capture" | "analyze" | "recall";

export const INTENT_MODE_LABELS: Record<
  IntentMode,
  { label: string; hint: string; placeholder: string }
> = {
  ask: { label: "提问", hint: "向系统提问并获取回答", placeholder: "例如：embedding 为什么变慢了？" },
  capture: { label: "记录", hint: "写入长期记忆", placeholder: "例如：我的目标是…" },
  analyze: { label: "分析", hint: "重新压缩运行历史，生成新结论", placeholder: "可选：指定分析关注点" },
  recall: { label: "回忆", hint: "从记忆中检索相关内容", placeholder: "输入关键词…" },
};
