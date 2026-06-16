"use client";

import { useMemo } from "react";
import { useExecutionStatus } from "./useExecutionStatus";

export type EmbeddingStatus = {
  activeMode: "ollama" | "hash";
  label: string;
  title: string;
  model: string;
  activeProvider: string | null;
};

const TITLE =
  "向量模式：存储导入时生成 embedding；Chat/回忆检索时再次 embedding 查询。\n" +
  "反思不走 embedding provider（Chat 时用大模型；批量反思在 sleep-time 后台）。";

export function useEmbeddingStatus(): EmbeddingStatus | null {
  const { status } = useExecutionStatus();

  return useMemo(() => {
    if (status.loading && !status.runtimeConnected) return null;
    if (status.error?.includes("Demo")) {
      return {
        activeMode: "hash",
        label: "Demo",
        title: "Demo 模式：本地演示，不连接 Runtime embedding",
        model: "",
        activeProvider: null,
      };
    }
    if (!status.runtimeConnected) return null;

    const activeProvider = status.activeEmbedProvider;
    const ollama = activeProvider === "ollama";
    return {
      activeMode: ollama ? "ollama" : "hash",
      label: ollama ? "Ollama" : "Hash",
      title: TITLE,
      model: String(status.embedding.model ?? ""),
      activeProvider,
    };
  }, [status]);
}
