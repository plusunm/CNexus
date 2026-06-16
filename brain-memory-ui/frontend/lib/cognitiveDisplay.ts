import type { CognitiveActionBlock } from "./cognitiveTypes";

/** 面向用户的中文展示层 — 隐藏工程 action id */
export const ACTION_DISPLAY: Record<
  string,
  { title: string; subtitle: string; cta: string }
> = {
  enable_aggressive_embed_cache: {
    title: "优先使用 embedding 缓存",
    subtitle: "减少重复向量计算，缓解本地推理压力",
    cta: "启用缓存策略",
  },
  restore_ollama_embedding: {
    title: "恢复 Ollama 语义向量",
    subtitle: "提升记忆召回质量（需 Ollama 在线）",
    cta: "切换为 Ollama embed",
  },
  defer_full_cognitive_loop: {
    title: "降低后台认知负载",
    subtitle: "在当前算力下优先保证对话与推理稳定",
    cta: "切换为稳妥模式",
  },
  continue_monitoring: {
    title: "系统运行平稳",
    subtitle: "暂无需要立即处理的结构性问题",
    cta: "继续观察",
  },
};

export function displayAction(action: CognitiveActionBlock) {
  const mapped = ACTION_DISPLAY[action.action];
  return {
    title: mapped?.title ?? action.rationale.slice(0, 24),
    subtitle: mapped?.subtitle ?? action.rationale,
    cta: mapped?.cta ?? "应用",
    why: action.why || action.rationale,
    priority: action.priority,
    impact: action.impact ?? 0.7,
    reversibility: action.reversibility ?? 0.8,
    raw: action.action,
  };
}

export function priorityLabel(p: number): string {
  if (p >= 0.85) return "高优先级";
  if (p >= 0.6) return "中优先级";
  return "低优先级";
}

export function reversibilityLabel(r: number): string {
  if (r >= 0.9) return "可随时撤回";
  if (r >= 0.6) return "可部分撤回";
  return "变更需谨慎";
}
