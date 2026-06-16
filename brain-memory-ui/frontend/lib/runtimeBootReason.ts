import type { BilingualLabel } from "@/lib/spine/labels";

/** Backend `/v1/system/ready` blocking reason codes. */
export type RuntimeBootReason =
  | "API_STARTING"
  | "RUNTIME_INIT"
  | "STORAGE_INIT"
  | "STORAGE_HYDRATE"
  | "COGNITIVE_WARMUP"
  | "L3_QUEUE_DRAIN"
  | "COGNITIVE_WARMUP_TIMEOUT"
  | "COGNITIVE_OFFLOAD_TIMEOUT"
  | "NOT_READY"
  | "UNKNOWN"
  | string
  | null;

const REASON_LABELS: Record<string, BilingualLabel> = {
  API_STARTING: { en: "Starting API…", zh: "正在启动 API…" },
  RUNTIME_INIT: { en: "Initializing runtime…", zh: "正在初始化运行时…" },
  STORAGE_INIT: { en: "Preparing storage…", zh: "正在准备存储…" },
  STORAGE_HYDRATE: { en: "Loading memory index…", zh: "正在加载记忆索引…" },
  COGNITIVE_WARMUP: { en: "Loading cognitive engine…", zh: "正在加载认知引擎…" },
  L3_QUEUE_DRAIN: { en: "Draining task queue…", zh: "正在清空任务队列…" },
  COGNITIVE_WARMUP_TIMEOUT: {
    en: "Cognitive warmup slow — entering basic mode…",
    zh: "认知预热较慢，正在进入基础模式…",
  },
  COGNITIVE_OFFLOAD_TIMEOUT: {
    en: "Cognitive service busy — retry shortly",
    zh: "认知服务繁忙，请稍候重试",
  },
  NOT_READY: { en: "Runtime not ready", zh: "Runtime 未就绪" },
  UNKNOWN: { en: "Starting…", zh: "正在启动…" },
};

export function formatRuntimeBootLabel(
  reason: RuntimeBootReason,
  progress: number | null | undefined,
  locale: "zh" | "en" = "zh",
): string {
  if (!reason) return locale === "zh" ? "运行时已连接" : "Runtime connected";
  const base = REASON_LABELS[reason]?.[locale] ?? REASON_LABELS.UNKNOWN[locale];
  if (progress == null || progress >= 100) return base;
  return `${base} (${Math.round(progress)}%)`;
}

export function extractBootStatus(payload: {
  status?: string;
  ready?: boolean;
  reason?: RuntimeBootReason;
  progress?: number;
  boot_phase?: string;
}): {
  ready: boolean;
  reason: RuntimeBootReason;
  progress: number | null;
} {
  const ready =
    payload.ready === true ||
    (payload.status === "ready" && payload.boot_phase === "boot_4_ready");
  return {
    ready,
    reason: ready ? null : (payload.reason ?? null),
    progress: ready ? 100 : (payload.progress ?? null),
  };
}
