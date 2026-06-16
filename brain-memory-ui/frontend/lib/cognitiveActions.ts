"use client";

import type { CognitiveActionBlock } from "./cognitiveTypes";
import { useCnexusConfigStore, validateConfig } from "./cnexusConfigStore";

export type ActionApplyResult = {
  ok: boolean;
  message: string;
};

/** Map CSE action strings → governed config updates (UI closed loop). */
export function executeCognitiveAction(action: CognitiveActionBlock): ActionApplyResult {
  const { updateConfig, setLastAction } = useCnexusConfigStore.getState();

  switch (action.action) {
    case "enable_aggressive_embed_cache":
      updateConfig({
        scheduler: { max_concurrency: 1, embed_chat_mutex: true },
        cse: { enabled: true, window_size: 150, auto_synthesize: true },
      });
      setLastAction(action.action);
      return { ok: true, message: "已启用 cache-first + 单并发策略" };

    case "restore_ollama_embedding":
      updateConfig({
        model: {
          llm_provider: "ollama",
          chat_model: useCnexusConfigStore.getState().config.model.chat_model,
          embedding_model: "nomic-embed-text",
        },
      });
      setLastAction(action.action);
      return { ok: true, message: "已标记恢复 Ollama embedding（需 Runtime 在线）" };

    case "defer_full_cognitive_loop":
      updateConfig({ cse: { enabled: true, window_size: 100, auto_synthesize: true } });
      setLastAction(action.action);
      return { ok: true, message: "已切换为 safe 认知策略（本地 Store）" };

    case "continue_monitoring":
      setLastAction(action.action);
      return { ok: true, message: "继续观测 — 无配置变更" };

    default:
      return { ok: false, message: `未知动作：${action.action}` };
  }
}

export { validateConfig };
