"use client";

import { useEffect, useMemo, useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { brainApi } from "@/lib/api";
import { useMindOverview } from "@/cnexus-kernel";
import { useEmbeddingStatus } from "@/hooks/useEmbeddingStatus";
import { EmbeddingModeBadge } from "./EmbeddingModeBadge";
import { OllamaControlButton } from "./OllamaControlButton";
import { useMindTheme } from "./MindUiProvider";

const TABS = ["全部", "身份", "目标", "信念", "经历"] as const;
const EMBEDDING_TABS = new Set<(typeof TABS)[number]>(["信念", "经历"]);
const TAB_TO_TAG: Record<(typeof TABS)[number], string | null> = {
  全部: null,
  身份: "identity",
  目标: "goal",
  信念: "belief",
  经历: "episode",
};

type PanelVariant = "overview" | "cognitive" | "float";

export function MemoryPanel({ variant = "overview" }: { variant?: PanelVariant }) {
  const t = useMindTheme();
  const isCognitive = variant === "cognitive" || variant === "float";
  const isFloat = variant === "float";
  const { overview, isDemo, isLive, isFallback } = useMindOverview();
  const embeddingStatus = useEmbeddingStatus();
  const [tab, setTab] = useState<(typeof TABS)[number]>("全部");
  const [query, setQuery] = useState("");
  const [recallPreview, setRecallPreview] = useState<string | null>(null);
  const [recallBusy, setRecallBusy] = useState(false);
  const [memoryStats, setMemoryStats] = useState<string | null>(null);

  const tagColor = (tag: string) => {
    if (tag === "goal") return t.blue;
    if (tag === "belief") return t.green;
    if (tag === "episode") return t.textMuted;
    return t.blue;
  };

  const runSemanticRecall = async () => {
    if (!query.trim() || isDemo) return;
    setRecallBusy(true);
    setRecallPreview(null);
    try {
      const { context } = await brainApi.recall(query.trim());
      setRecallPreview(context.slice(0, 600) || "无匹配记忆");
    } catch {
      setRecallPreview("语义检索失败 — Runtime 未连接");
    } finally {
      setRecallBusy(false);
    }
  };

  const loadStats = async () => {
    if (isDemo) return;
    try {
      const stats = await brainApi.memoryStats();
      setMemoryStats(`共 ${stats.total} 条 · 平均重要度 ${(stats.avg_importance * 100).toFixed(0)}%`);
    } catch {
      setMemoryStats(null);
    }
  };

  useEffect(() => {
    if (!isDemo && (isLive || isFallback)) void loadStats();
  }, [isDemo, isLive, isFallback, overview.memory_items.length]);

  const items = useMemo(() => {
    const tag = TAB_TO_TAG[tab];
    const indexed = overview.memory_items.map((item, sourceIndex) => ({ item, sourceIndex }));
    let rows = indexed;
    if (tag) rows = rows.filter((row) => row.item.tag === tag);
    if (query.trim()) {
      const q = query.trim().toLowerCase();
      rows = rows.filter(
        (row) =>
          row.item.title.toLowerCase().includes(q) ||
          row.item.desc.toLowerCase().includes(q) ||
          row.item.meta.toLowerCase().includes(q),
      );
    }
    return rows
      .sort((a, b) => b.sourceIndex - a.sourceIndex)
      .map((row) => row.item);
  }, [overview.memory_items, tab, query]);

  const rootClass = isFloat
    ? "cnexus-float-panel flex flex-col h-full min-h-0 min-w-0"
    : `rounded-xl border flex flex-col ${
        variant === "overview" ? "h-[360px]" : "h-[420px]"
      } ${isCognitive ? "opacity-95" : "shadow-sm"}`;

  return (
    <div
      className={rootClass}
      style={{
        backgroundColor: t.surface,
        borderColor: t.border,
        borderTopWidth: isFloat ? undefined : isCognitive ? 1 : 3,
        borderTopColor: isFloat ? undefined : isCognitive ? t.border : t.blue,
      }}
      data-cnexus-memory-panel
    >
      <div
        className="px-3 pt-3 pb-2 border-b shrink-0"
        style={{ borderColor: t.border, backgroundColor: isFloat ? "rgba(0,0,0,0.08)" : undefined }}
        data-no-drag
      >
        {!isCognitive && !isFloat && (
          <p className="text-sm font-semibold mb-2 px-1" style={{ color: t.blue }}>
            Memory 浏览面板
          </p>
        )}
        {isFloat && (
          <div className="flex items-center justify-end mb-2">
            <OllamaControlButton compact />
          </div>
        )}
        <div className="flex gap-1 mb-2 flex-wrap">
          {TABS.map((label) => (
            <button
              key={label}
              type="button"
              className="px-2.5 py-1 rounded-md text-xs"
              style={{
                backgroundColor: tab === label ? t.blueSoft : "transparent",
                color: tab === label ? t.blue : t.textMuted,
                fontWeight: tab === label ? 600 : 400,
              }}
              onClick={() => setTab(label)}
            >
              <span className="inline-flex items-center gap-1">
                {label}
                {EMBEDDING_TABS.has(label) && <EmbeddingModeBadge status={embeddingStatus} compact />}
              </span>
            </button>
          ))}
        </div>
        <div className="pr-0.5 flex gap-2">
          <input
            className="flex-1 min-w-0 text-xs px-2.5 py-1.5 rounded-lg border outline-none box-border"
            style={{ borderColor: t.border, backgroundColor: t.bg, color: t.text }}
            placeholder="搜索记忆…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !isDemo) void runSemanticRecall();
            }}
          />
          {!isDemo && (
            <button
              type="button"
              className="shrink-0 px-2 py-1 rounded-lg text-[10px] font-medium text-white disabled:opacity-50"
              style={{ backgroundColor: t.blue }}
              disabled={recallBusy || !query.trim()}
              onClick={() => void runSemanticRecall()}
            >
              语义
            </button>
          )}
        </div>
        {memoryStats && (
          <p className="text-[10px] mt-1.5 px-0.5" style={{ color: t.textLight }}>
            Runtime · {memoryStats}
          </p>
        )}
        {recallPreview && (
          <p
            className="text-[10px] mt-2 px-2 py-1.5 rounded-lg border whitespace-pre-wrap max-h-24 overflow-y-auto cnexus-float-scroll"
            style={{ borderColor: t.border, color: t.textMuted, backgroundColor: t.bg }}
          >
            {recallPreview}
          </p>
        )}
        {isFallback && (
          <p className="text-[10px] mt-2 px-0.5" style={{ color: t.orange }}>
            Runtime 重连中 — 数据仍走本地 API
          </p>
        )}
        {EMBEDDING_TABS.has(tab) && embeddingStatus && (
          <p className="text-[10px] mt-2 px-0.5 leading-relaxed" style={{ color: t.textLight }}>
            模式 · {embeddingStatus.label}
            {embeddingStatus.activeMode === "hash" ? " 降级" : ""}
            {embeddingStatus.model ? ` · ${embeddingStatus.model}` : ""} — 导入时写入、检索时查询；反思不走此通道
          </p>
        )}
        {isFloat && (!EMBEDDING_TABS.has(tab) || !embeddingStatus) && (
          <p className="text-[10px] mt-2 px-0.5" style={{ color: t.textLight }}>
            最新在上 · 可上下滚动浏览
          </p>
        )}
      </div>

      <div
        className={`flex-1 min-h-0 overflow-y-auto overscroll-contain cnexus-float-scroll ${
          isFloat ? "px-2 py-2 mr-0.5" : "p-2"
        }`}
        data-no-drag
      >
        {items.length === 0 && (
          <p className="text-xs p-4 text-center" style={{ color: t.textMuted }}>
            暂无匹配记忆
          </p>
        )}
        <div className="space-y-1">
        {items.map((item) => {
          const color = tagColor(item.tag);
          return (
            <div
              key={item.id}
              className="flex items-start gap-2 p-2 rounded-lg hover:opacity-100 opacity-80 hover:bg-white/5 transition group"
            >
              <div
                className="w-8 h-8 rounded-lg shrink-0 mt-0.5"
                style={{ backgroundColor: `${color}22` }}
              />
              <div className="flex-1 min-w-0 pr-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span
                    className={`truncate ${item.tag === "goal" ? "text-sm font-semibold" : "text-sm font-medium"}`}
                    style={{ color: item.tag === "goal" ? t.blue : t.text }}
                  >
                    {item.title}
                  </span>
                  <span
                    className="text-[10px] px-1.5 py-0.5 rounded shrink-0"
                    style={{ backgroundColor: `${color}18`, color }}
                  >
                    {item.tag}
                  </span>
                </div>
                <p className="text-[11px] break-words whitespace-pre-wrap" style={{ color: t.textMuted }}>
                  {item.desc}
                </p>
                <p
                  className="text-[10px] break-words"
                  style={{ color: t.textLight, fontFamily: t.fontMono }}
                >
                  {item.meta}
                </p>
              </div>
              {!isCognitive && !isFloat && (
                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition shrink-0">
                  <Pencil className="w-3.5 h-3.5" style={{ color: t.textLight }} />
                  <Trash2 className="w-3.5 h-3.5" style={{ color: t.textLight }} />
                </div>
              )}
            </div>
          );
        })}
        </div>
      </div>
    </div>
  );
}
