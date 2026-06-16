"use client";

import { useEffect, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { cnexusProductApi } from "@/lib/api";
import {
  CONFIG_PRESETS,
  type ConfigPresetId,
} from "@/lib/cognitiveTypes";
import { useCnexusConfigStore } from "@/lib/cnexusConfigStore";
import { useMindTheme } from "../MindUiProvider";

export function SystemControlPanel() {
  const t = useMindTheme();
  const [open, setOpen] = useState(false);
  const [advanced, setAdvanced] = useState(false);
  const [runtimeStatus, setRuntimeStatus] = useState<Record<string, unknown> | null>(null);
  const { config, activePreset, applyPreset, updateConfig } = useCnexusConfigStore();

  useEffect(() => {
    void cnexusProductApi.executionStatus().then(setRuntimeStatus).catch(() => setRuntimeStatus(null));
  }, []);

  const envelope = String(runtimeStatus?.runtime_envelope || "—");

  return (
    <section className="rounded-xl border overflow-hidden" style={{ borderColor: t.border, backgroundColor: t.surface }}>
      <button
        type="button"
        className="w-full flex items-center gap-2 px-4 py-3 text-left"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? (
          <ChevronDown className="w-4 h-4" style={{ color: t.textMuted }} />
        ) : (
          <ChevronRight className="w-4 h-4" style={{ color: t.textMuted }} />
        )}
        <span className="text-sm font-medium" style={{ color: t.text }}>
          System Control
        </span>
        <span className="text-[10px] ml-auto" style={{ color: t.textLight, fontFamily: t.fontMono }}>
          preset={activePreset || "custom"} · {envelope}
        </span>
      </button>

      {open && (
        <div className="px-4 pb-4 border-t space-y-4" style={{ borderColor: t.border }}>
          {/* Level 1: Presets */}
          <div>
            <p className="text-[10px] uppercase mb-2 pt-3" style={{ color: t.blue, fontFamily: t.fontMono }}>
              Presets · 一键模式
            </p>
            <div className="flex flex-wrap gap-2">
              {(Object.keys(CONFIG_PRESETS) as ConfigPresetId[]).map((id) => {
                const preset = CONFIG_PRESETS[id];
                const active = activePreset === id;
                return (
                  <button
                    key={id}
                    type="button"
                    title={preset.description}
                    onClick={() => applyPreset(id)}
                    className="px-3 py-2 rounded-lg border text-left min-w-[120px]"
                    style={{
                      borderColor: active ? t.blue : t.border,
                      backgroundColor: active ? t.blueSoft : t.chatBg,
                    }}
                  >
                    <span className="text-xs font-medium block" style={{ color: active ? t.blue : t.text }}>
                      {preset.label}
                    </span>
                    <span className="text-[10px]" style={{ color: t.textLight }}>
                      {preset.description}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Level 2: Core 3 controls */}
          <div>
            <p className="text-[10px] uppercase mb-2" style={{ color: t.orange, fontFamily: t.fontMono }}>
              Core · 三核心开关
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <label className="rounded-lg border p-3 flex flex-col gap-2" style={{ borderColor: t.border, backgroundColor: t.chatBg }}>
                <span className="text-xs" style={{ color: t.textMuted }}>
                  Max Concurrency
                </span>
                <input
                  type="range"
                  min={1}
                  max={2}
                  value={config.scheduler.max_concurrency}
                  onChange={(e) =>
                    updateConfig({
                      scheduler: {
                        max_concurrency: Number(e.target.value),
                        embed_chat_mutex: config.scheduler.embed_chat_mutex,
                      },
                    })
                  }
                />
                <span className="text-[10px]" style={{ fontFamily: t.fontMono, color: t.text }}>
                  {config.scheduler.max_concurrency}
                </span>
              </label>
              <label className="rounded-lg border p-3 flex items-center gap-2" style={{ borderColor: t.border, backgroundColor: t.chatBg }}>
                <input
                  type="checkbox"
                  checked={config.scheduler.embed_chat_mutex}
                  onChange={(e) =>
                    updateConfig({
                      scheduler: {
                        embed_chat_mutex: e.target.checked,
                        max_concurrency: config.scheduler.max_concurrency,
                      },
                    })
                  }
                />
                <span className="text-xs" style={{ color: t.textMuted }}>
                  Embed/Chat Mutex
                </span>
              </label>
              <label className="rounded-lg border p-3 flex items-center gap-2" style={{ borderColor: t.border, backgroundColor: t.chatBg }}>
                <input
                  type="checkbox"
                  checked={config.cse.auto_synthesize}
                  onChange={(e) =>
                    updateConfig({
                      cse: {
                        ...config.cse,
                        auto_synthesize: e.target.checked,
                      },
                    })
                  }
                />
                <span className="text-xs" style={{ color: t.textMuted }}>
                  Auto Synthesize
                </span>
              </label>
            </div>
          </div>

          {/* Level 3: Advanced */}
          <button
            type="button"
            className="text-[10px] flex items-center gap-1"
            style={{ color: t.textLight }}
            onClick={() => setAdvanced((v) => !v)}
          >
            {advanced ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            Advanced JSON preview
          </button>
          {advanced && (
            <pre
              className="text-[10px] p-3 rounded-lg overflow-auto max-h-40"
              style={{ backgroundColor: t.chatBg, color: t.textMuted, fontFamily: t.fontMono }}
            >
              {JSON.stringify(config, null, 2)}
            </pre>
          )}
        </div>
      )}
    </section>
  );
}
