"use client";

import { Brain, LayoutGrid, PanelTop } from "lucide-react";
import { MODE_LABELS, type MindUiMode } from "./themes/types";
import { useMindUi } from "./MindUiProvider";

export function MindModeSwitch({ compact }: { compact?: boolean }) {
  const { mode, setMode, theme } = useMindUi();

  const options: MindUiMode[] = ["overview", "cognitive", "float"];

  return (
    <div
      className="inline-flex rounded-lg border p-0.5 gap-0.5"
      style={{ borderColor: theme.border, backgroundColor: theme.surface }}
      role="tablist"
      aria-label="UI 模式切换"
    >
      {options.map((m) => {
        const active = mode === m;
        const Icon = m === "overview" ? LayoutGrid : m === "cognitive" ? Brain : PanelTop;
        return (
          <button
            key={m}
            type="button"
            role="tab"
            aria-selected={active}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition"
            style={{
              backgroundColor: active ? theme.sidebarActive : "transparent",
              color: active ? theme.blue : theme.textMuted,
            }}
            onClick={() => setMode(m)}
            title={MODE_LABELS[m].subtitle}
          >
            <Icon className="w-3.5 h-3.5" />
            {!compact && MODE_LABELS[m].title}
          </button>
        );
      })}
    </div>
  );
}
