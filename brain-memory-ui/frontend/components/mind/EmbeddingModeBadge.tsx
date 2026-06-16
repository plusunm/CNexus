"use client";

import type { EmbeddingStatus } from "@/hooks/useEmbeddingStatus";
import { useMindTheme } from "./MindUiProvider";

type Props = {
  status: EmbeddingStatus | null;
  compact?: boolean;
};

export function EmbeddingModeBadge({ status, compact = false }: Props) {
  const t = useMindTheme();
  if (!status) return null;

  const color = status.activeMode === "ollama" ? t.green : t.orange;

  return (
    <span
      className={`inline-flex items-center rounded shrink-0 font-medium ${
        compact ? "text-[9px] px-1 py-0" : "text-[10px] px-1.5 py-0.5"
      }`}
      style={{
        color,
        backgroundColor: `${color}18`,
        border: `1px solid ${color}44`,
      }}
      title={status.title}
    >
      {status.label}
    </span>
  );
}
