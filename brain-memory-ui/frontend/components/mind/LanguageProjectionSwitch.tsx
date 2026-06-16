"use client";

import { Languages } from "lucide-react";
import {
  loadLanguageProjection,
  PROJECTION_LABELS,
  saveLanguageProjection,
  type LanguageProjectionMode,
} from "@/lib/sibt/projectionMode";
import { useMindTheme } from "./MindUiProvider";
import { useCallback, useEffect, useState } from "react";

const MODES: LanguageProjectionMode[] = ["zh", "en", "both"];

type Props = {
  compact?: boolean;
  onChange?: (mode: LanguageProjectionMode) => void;
};

export function LanguageProjectionSwitch({ compact, onChange }: Props) {
  const theme = useMindTheme();
  const [mode, setMode] = useState<LanguageProjectionMode>("zh");

  useEffect(() => {
    setMode(loadLanguageProjection());
  }, []);

  const select = useCallback(
    (next: LanguageProjectionMode) => {
      setMode(next);
      saveLanguageProjection(next);
      onChange?.(next);
      window.dispatchEvent(new CustomEvent("cnexus:projection-change", { detail: next }));
    },
    [onChange],
  );

  return (
    <div
      className="inline-flex rounded-lg border p-0.5 gap-0.5"
      style={{ borderColor: theme.border, backgroundColor: theme.surface }}
      role="tablist"
      aria-label="语言投影"
    >
      {MODES.map((m) => {
        const active = mode === m;
        return (
          <button
            key={m}
            type="button"
            role="tab"
            aria-selected={active}
            className="flex items-center gap-1 px-2 py-1.5 rounded-md text-xs font-medium transition"
            style={{
              backgroundColor: active ? theme.sidebarActive : "transparent",
              color: active ? theme.blue : theme.textMuted,
            }}
            onClick={() => select(m)}
            title={PROJECTION_LABELS[m].subtitle}
          >
            {m === "both" && <Languages className="w-3.5 h-3.5" />}
            {!compact && PROJECTION_LABELS[m].title}
          </button>
        );
      })}
    </div>
  );
}

export function useLanguageProjection(): LanguageProjectionMode {
  const [mode, setMode] = useState<LanguageProjectionMode>("zh");

  useEffect(() => {
    setMode(loadLanguageProjection());
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<LanguageProjectionMode>).detail;
      if (detail) setMode(detail);
    };
    window.addEventListener("cnexus:projection-change", handler);
    return () => window.removeEventListener("cnexus:projection-change", handler);
  }, []);

  return mode;
}
