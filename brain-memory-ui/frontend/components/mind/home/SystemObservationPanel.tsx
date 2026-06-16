"use client";

import { useState } from "react";
import { ChevronRight, Eye } from "lucide-react";
import type { CognitiveOutput, CognitiveTextBlock } from "@/lib/cognitiveTypes";
import {
  insightCardsForDisplay,
  isFirstSeen,
  sortDiscoveries,
  type ValueDetail,
} from "@/lib/cognitiveValue";
import { useMindTheme } from "../MindUiProvider";
import { CognitiveValueDrawer } from "./CognitiveValueDrawer";

type TabId = "summary" | "patterns" | "experiences" | "discoveries";

const TABS: { id: TabId; label: string }[] = [
  { id: "summary", label: "发生了什么" },
  { id: "patterns", label: "发现的规律" },
  { id: "experiences", label: "经验归纳" },
  { id: "discoveries", label: "新发现" },
];

function DetailList({
  items,
  onSelect,
}: {
  items: CognitiveTextBlock[];
  onSelect?: (item: CognitiveTextBlock) => void;
}) {
  const t = useMindTheme();
  if (!items.length) {
    return (
      <p className="text-sm py-8 text-center" style={{ color: t.textLight }}>
        暂无内容 — 多使用系统后会自动积累
      </p>
    );
  }
  return (
    <ul className="space-y-2.5">
      {items.map((item, i) => (
        <li key={`${item.source}-${i}`}>
          <button
            type="button"
            onClick={() => onSelect?.(item)}
            className="w-full text-left text-sm leading-relaxed rounded-lg px-3 py-2.5 border transition-opacity hover:opacity-90"
            style={{ borderColor: t.border, backgroundColor: t.chatBg, color: t.text }}
          >
            {item.text}
          </button>
        </li>
      ))}
    </ul>
  );
}

type Props = {
  data: CognitiveOutput;
  loading?: boolean;
  error?: string | null;
  isExample?: boolean;
  isEmpty?: boolean;
  /** 工作台已有独立「价值总结」卡片时，此处不再重复 narrative */
  hideNarrative?: boolean;
};

/** 顶部 — 系统观察 */
export function SystemObservationPanel({
  data,
  loading,
  error,
  isExample,
  isEmpty,
  hideNarrative = false,
}: Props) {
  const t = useMindTheme();
  const [tab, setTab] = useState<TabId>("summary");
  const [drawer, setDrawer] = useState<ValueDetail | null>(null);

  const insights = insightCardsForDisplay(data, 4);
  const discoveries = sortDiscoveries(data.discoveries ?? []);
  const experiences = data.experiences?.length ? data.experiences : data.rules;

  const tabItems =
    tab === "summary"
      ? data.summary
      : tab === "patterns"
        ? data.patterns
        : tab === "experiences"
          ? experiences
          : [];

  const tabLabel = TABS.find((x) => x.id === tab)?.label ?? "";

  return (
    <>
      <section
        className="rounded-2xl border overflow-hidden"
        style={{ borderColor: t.border, backgroundColor: t.surface }}
      >
        <div
          className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 px-4 py-3 border-b"
          style={{ borderColor: t.border, backgroundColor: t.chatBg }}
        >
          <div className="flex items-center gap-2 min-w-0">
            <Eye className="w-4 h-4 shrink-0" style={{ color: t.purple }} />
            <h3 className="text-sm font-semibold" style={{ color: t.text }}>
              系统观察
            </h3>
            {discoveries.length > 0 && (
              <span
                className="text-[10px] px-1.5 py-0.5 rounded-full shrink-0"
                style={{ backgroundColor: t.orangeSoft, color: t.orange }}
              >
                {discoveries.length} 条新发现
              </span>
            )}
          </div>
          <div className="flex gap-1 p-0.5 rounded-lg overflow-x-auto" style={{ backgroundColor: t.bg }}>
            {TABS.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setTab(item.id)}
                className="px-2.5 py-1.5 rounded-md text-[11px] font-medium whitespace-nowrap"
                style={{
                  backgroundColor: tab === item.id ? t.surface : "transparent",
                  color: tab === item.id ? t.blue : t.textMuted,
                  boxShadow: tab === item.id ? `0 0 0 1px ${t.border}` : undefined,
                }}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        {isEmpty && !loading && (
          <div className="px-4 py-6 text-center border-b" style={{ borderColor: t.border }}>
            <p className="text-sm mb-1" style={{ color: t.text }}>
              {error ? "无法加载认知结论" : "暂无运行数据"}
            </p>
            <p className="text-xs" style={{ color: t.textMuted }}>
              {error ?? "连接 Runtime 后使用提问、记录或分析，系统才会生成价值总结"}
            </p>
          </div>
        )}

        {data.narrative && !isEmpty && !hideNarrative && (
          <div
            className="px-4 py-3 border-b text-sm leading-relaxed"
            style={{ borderColor: t.border, color: t.textMuted, backgroundColor: `${t.blueSoft}` }}
          >
            <span className="text-[11px] font-medium" style={{ color: t.blue }}>
              价值总结
            </span>
            <p className="mt-1" style={{ color: t.text }}>
              {data.narrative}
            </p>
            <p className="text-[10px] mt-2" style={{ color: t.textLight }}>
              {isExample
                ? "示例综合摘要 — 下方 Tab 为演示结构"
                : "综合事实、解读、新变化与建议 — 下方各 Tab 展开细节"}
            </p>
          </div>
        )}

        <div
          className="grid grid-cols-1 md:grid-cols-2"
          style={{ borderTop: data.narrative ? undefined : `1px solid ${t.border}` }}
        >
          <div className="p-4 min-h-[140px] md:border-r" style={{ borderColor: t.border }}>
            {tab === "discoveries" ? (
              <>
                <p className="text-[10px] uppercase tracking-wider mb-3" style={{ color: t.textLight }}>
                  新发现
                </p>
                {discoveries.length > 0 ? (
                  <ul className="space-y-2">
                    {discoveries.map((item) => (
                      <li key={item.id}>
                        <button
                          type="button"
                          onClick={() => setDrawer({ kind: "discovery", item })}
                          className="w-full text-left rounded-lg px-3 py-2.5 border"
                          style={{ borderColor: t.orange, backgroundColor: t.orangeSoft, color: t.text }}
                        >
                          <div className="flex items-center justify-between gap-2 mb-1">
                            <span className="text-sm font-medium">{item.title}</span>
                            <span className="text-[10px]" style={{ color: t.orange }}>
                              新 {Math.round(item.novelty * 100)}%
                            </span>
                          </div>
                          <p className="text-xs leading-relaxed" style={{ color: t.textMuted }}>
                            {item.description}
                          </p>
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm py-8 text-center" style={{ color: t.textLight }}>
                    继续使用后，系统会对比历史窗口并标记首次出现的价值
                  </p>
                )}
              </>
            ) : (
              <>
                <p className="text-[10px] uppercase tracking-wider mb-3" style={{ color: t.textLight }}>
                  {tabLabel}
                </p>
                <DetailList
                  items={tabItems}
                  onSelect={(item) => setDrawer({ kind: "text", item, label: tabLabel })}
                />
              </>
            )}
          </div>

          <div className="p-4">
            <p className="text-[10px] uppercase tracking-wider mb-3" style={{ color: t.textLight }}>
              关键洞察
            </p>
            {insights.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {insights.map((item, i) => (
                  <button
                    key={`${item.source}-${i}`}
                    type="button"
                    onClick={() => setDrawer({ kind: "insight", item })}
                    className="rounded-xl p-3 border h-full text-left transition-opacity hover:opacity-90"
                    style={{ borderColor: t.border, backgroundColor: t.chatBg }}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1.5">
                      <span className="text-xs font-medium leading-snug" style={{ color: t.text }}>
                        {item.title}
                      </span>
                      <div className="flex flex-col items-end gap-1 shrink-0">
                        <span
                          className="text-[10px] px-1.5 py-0.5 rounded"
                          style={{ backgroundColor: t.purpleSoft, color: t.purple }}
                        >
                          {Math.round(item.confidence * 100)}%
                        </span>
                        {isFirstSeen(item.novelty) && (
                          <span
                            className="text-[9px] px-1 rounded"
                            style={{ backgroundColor: t.orangeSoft, color: t.orange }}
                          >
                            首次
                          </span>
                        )}
                      </div>
                    </div>
                    <p className="text-[11px] leading-relaxed line-clamp-2" style={{ color: t.textMuted }}>
                      {item.description}
                    </p>
                  </button>
                ))}
              </div>
            ) : (
              <p
                className="text-sm py-6 text-center rounded-xl border border-dashed"
                style={{ color: t.textLight, borderColor: t.border }}
              >
                洞察将在有足够运行数据后生成
              </p>
            )}
          </div>
        </div>

        <div className="px-4 py-2 border-t flex justify-end" style={{ borderColor: t.border }}>
          <button
            type="button"
            onClick={() =>
              setDrawer(
                insights[0]
                  ? { kind: "insight", item: insights[0] }
                  : discoveries[0]
                    ? { kind: "discovery", item: discoveries[0] }
                    : null,
              )
            }
            className="inline-flex items-center gap-1 text-xs font-medium"
            style={{ color: t.blue }}
          >
            展开完整思考
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </section>

      {drawer && (
        <CognitiveValueDrawer
          detail={drawer}
          onClose={() => setDrawer(null)}
        />
      )}
    </>
  );
}
