"use client";

import { useState } from "react";
import type { ExecLogEvent, ExecTraceManifest } from "@/lib/cognitiveTypes";
import { CONFIG_PRESETS, type ConfigPresetId } from "@/lib/cognitiveTypes";
import { useCnexusConfigStore } from "@/lib/cnexusConfigStore";
import { bi, biFmt, homeL, navL } from "@/lib/spine/labels";
import { useMindTheme } from "../MindUiProvider";
import { HomeModelSettingsPanel } from "./HomeModelSettingsPanel";

type Tab = "trace" | "settings" | "model";

type Props = {
  logs: ExecLogEvent[];
  traces: ExecTraceManifest[];
  traceLoading: boolean;
  traceRefreshing?: boolean;
  onRefreshTrace: () => void;
};

export function HomeBottomPanel({ logs, traces, traceLoading, traceRefreshing, onRefreshTrace }: Props) {
  const t = useMindTheme();
  const [tab, setTab] = useState<Tab>("trace");
  const { config, activePreset, applyPreset, updateConfig } = useCnexusConfigStore();

  const tabs: { id: Tab; label: string }[] = [
    { id: "trace", label: bi(homeL.tabTrace) },
    { id: "settings", label: bi(homeL.tabSettings) },
    { id: "model", label: bi(homeL.tabModel) },
  ];

  return (
    <section
      className="rounded-2xl border overflow-hidden"
      style={{ borderColor: t.border, backgroundColor: t.surface }}
    >
      <div className="flex border-b overflow-x-auto" style={{ borderColor: t.border }}>
        {tabs.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setTab(item.id)}
            className="flex-1 min-w-[88px] py-3 text-sm font-medium whitespace-nowrap"
            style={{
              color: tab === item.id ? t.blue : t.textMuted,
              backgroundColor: tab === item.id ? t.blueSoft : "transparent",
              borderBottom: tab === item.id ? `2px solid ${t.blue}` : "2px solid transparent",
            }}
          >
            {item.label}
          </button>
        ))}
      </div>

      {tab === "trace" ? (
        <div className="max-h-[240px] overflow-auto">
          <div className="flex items-center justify-between px-4 py-2 border-b" style={{ borderColor: t.border }}>
            <span className="text-xs" style={{ color: t.textMuted }}>
              {biFmt(homeL.traceStats, { logs: logs.length, traces: traces.length })}
            </span>
            <button
              type="button"
              onClick={onRefreshTrace}
              className="text-xs px-2 py-1 rounded border"
              style={{ borderColor: t.border, color: t.textMuted }}
            >
              {traceLoading || traceRefreshing ? bi(homeL.refreshing) : bi(navL.refresh)}
            </button>
          </div>
          <ul>
            {[...logs].reverse().slice(0, 30).map((log) => (
              <li
                key={log.id}
                className="px-4 py-2.5 text-xs flex gap-3 border-b last:border-0"
                style={{ borderColor: t.border, color: t.textMuted }}
              >
                <span className="w-14 shrink-0" style={{ color: t.textLight }}>
                  {log.timestamp?.slice(11, 19) || "—"}
                </span>
                <span
                  className="w-10 shrink-0"
                  style={{
                    color: log.level === "error" ? t.red : log.level === "warn" ? t.orange : t.green,
                  }}
                >
                  {log.level === "error" ? bi(homeL.logLevelError) : log.level === "warn" ? bi(homeL.logLevelWarn) : bi(homeL.logLevelOk)}
                </span>
                <span className="min-w-0 truncate" style={{ color: t.text }}>
                  {log.message}
                </span>
              </li>
            ))}
            {logs.length === 0 && (
              <li className="py-10 text-center text-sm" style={{ color: t.textLight }}>
                {bi(homeL.noTraceLogs)}
              </li>
            )}
          </ul>
        </div>
      ) : tab === "settings" ? (
        <div className="p-4 space-y-4">
          <p className="text-xs" style={{ color: t.textMuted }}>
            {bi(homeL.runtimeModeHint)}
          </p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {(Object.keys(CONFIG_PRESETS) as ConfigPresetId[]).map((id) => {
              const preset = CONFIG_PRESETS[id];
              const active = activePreset === id;
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => applyPreset(id)}
                  className="text-left p-3 rounded-xl border transition-colors"
                  style={{
                    borderColor: active ? t.blue : t.border,
                    backgroundColor: active ? t.blueSoft : t.chatBg,
                  }}
                >
                  <span className="text-sm font-medium block" style={{ color: active ? t.blue : t.text }}>
                    {preset.label}
                  </span>
                  <span className="text-[11px] mt-1 block" style={{ color: t.textLight }}>
                    {preset.description}
                  </span>
                </button>
              );
            })}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
            <label className="text-xs space-y-2" style={{ color: t.textMuted }}>
              {bi(homeL.concurrencyMax)}
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
                className="w-full"
              />
            </label>
            <label className="flex items-center gap-2 text-xs" style={{ color: t.textMuted }}>
              <input
                type="checkbox"
                checked={config.cse.auto_synthesize}
                onChange={(e) =>
                  updateConfig({ cse: { ...config.cse, auto_synthesize: e.target.checked } })
                }
              />
              {bi(homeL.autoSynth)}
            </label>
          </div>
        </div>
      ) : (
        <HomeModelSettingsPanel />
      )}
    </section>
  );
}
