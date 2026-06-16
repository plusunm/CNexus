"use client";

import { useMemo } from "react";
import clsx from "clsx";
import { useOllamaStatus } from "@/hooks/useOllamaStatus";
import { useMindTheme } from "./MindUiProvider";
import { bi, connectionL } from "@/lib/spine/labels";

type Props = {
  compact?: boolean;
  inline?: boolean;
  className?: string;
};

export function OllamaConnectionBadge({ compact = false, inline = false, className }: Props) {
  const t = useMindTheme();
  const { status } = useOllamaStatus();

  const { label, color, connected, host } = useMemo(() => {
    if (status.loading || status.actionLoading) {
      return {
        label: bi(connectionL.ollamaProbing),
        color: t.textMuted,
        connected: false,
        host: status.host,
      };
    }
    if (status.running) {
      return {
        label: bi(connectionL.ollamaConnected),
        color: t.green,
        connected: true,
        host: status.host,
      };
    }
    return {
      label: bi(connectionL.ollamaDisconnected),
      color: t.red,
      connected: false,
      host: status.host,
    };
  }, [status, t.green, t.red, t.textMuted]);

  return (
    <div
      className={clsx(
        inline ? "inline-flex items-center gap-1 min-w-0" : "flex items-center gap-2",
        className,
      )}
      title={host ? `Ollama @ ${host}` : undefined}
    >
      <span
        className={clsx("rounded-full shrink-0", inline ? "w-1.5 h-1.5" : "w-2 h-2")}
        style={{
          backgroundColor: color,
          boxShadow: connected && !inline ? `0 0 6px ${color}` : undefined,
        }}
      />
      <span
        className={clsx(
          "font-medium truncate",
          inline ? "text-[10px]" : compact ? "text-[10px]" : "text-xs",
        )}
        style={{ color: connected ? color : t.textMuted }}
      >
        {label}
      </span>
    </div>
  );
}
