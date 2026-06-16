"use client";

import { useMindOverview } from "@/cnexus-kernel";
import { healthColor } from "@/lib/mindOverview";
import { useMindTheme } from "./MindUiProvider";
import type { MindTheme } from "./themes/types";

function FeedCard({
  title,
  accent,
  items,
  t,
}: {
  title: string;
  accent: string;
  items: string[];
  t: MindTheme;
}) {
  return (
    <div
      className="rounded-xl border p-3 min-h-[120px] shadow-sm"
      style={{ backgroundColor: t.surface, borderColor: t.border }}
    >
      <p className="text-xs font-semibold mb-2" style={{ color: accent }}>
        {title}
      </p>
      <ul className="space-y-1.5">
        {items.map((item, i) => (
          <li key={`${title}-${i}`} className="text-[11px] leading-snug" style={{ color: t.textMuted }}>
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ActivityFeedsRow({ compact }: { compact?: boolean }) {
  const t = useMindTheme();
  const { overview, runtimeLogs, isDemo } = useMindOverview();
  const { episodic, reflections, changes } = overview.feeds;
  const sys = overview.system;

  const logLines = runtimeLogs
    .slice(-3)
    .reverse()
    .map((l) => `${l.message.slice(0, 60)} · ${l.category}`);

  const changeItems = [...changes, ...logLines].slice(0, 3);

  return (
    <div className={`grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3 ${compact ? "mb-0" : "mb-3"}`}>
      <FeedCard
        title="最近经历 (Episodic)"
        accent={t.blue}
        t={t}
        items={
          episodic.length
            ? episodic.map((r) => `${r.text}${r.ago ? ` · ${r.ago}` : ""}`)
            : ["暂无经历记录"]
        }
      />
      <FeedCard
        title="最近反思 (Reflections)"
        accent={t.purple}
        t={t}
        items={
          reflections.length
            ? reflections.map((r) => `${r.text}${r.ago ? ` · ${r.ago}` : ""}`)
            : ["暂无反思记录"]
        }
      />
      <FeedCard
        title="最近变化 (Changes)"
        accent={t.orange}
        t={t}
        items={changeItems.length ? changeItems : ["Runtime stable"]}
      />
      <div
        className="rounded-xl border p-3 min-h-[120px] shadow-sm"
        style={{ backgroundColor: t.surface, borderColor: t.border }}
      >
        <p className="text-xs font-semibold mb-2" style={{ color: t.green }}>
          系统状态
        </p>
        <ul className="space-y-1.5 text-[11px]" style={{ color: t.textMuted }}>
          <li>
            认知健康度:{" "}
            <span style={{ color: healthColor(sys.health_label) }}>{sys.health_label}</span>
          </li>
          <li>记忆容量: {sys.memory_capacity_pct}%</li>
          <li>治理循环: {sys.governance_label}</li>
          <li>最后更新: {sys.last_update_ago}</li>
          {!isDemo && runtimeLogs.length > 0 && (
            <li>Runtime 日志: {runtimeLogs.length} 条</li>
          )}
        </ul>
      </div>
    </div>
  );
}
