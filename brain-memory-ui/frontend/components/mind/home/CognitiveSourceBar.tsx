"use client";

import { useMindConnection } from "@/cnexus-kernel";
import { formatGeneratedAt, getCognitiveSourceMeta } from "@/lib/cognitiveSource";
import { isReleaseBuild } from "@/lib/releaseBuild";
import { useMindTheme } from "../MindUiProvider";

type Props = {
  generatedAt?: string;
  windowSize?: number;
  onSwitchSource?: () => void;
};

/** 认知数据溯源条 — 切换数据源后必须让用户知道「现在看的是哪份数据」 */
export function CognitiveSourceBar({ generatedAt, windowSize, onSwitchSource }: Props) {
  const t = useMindTheme();
  const { effectiveMode } = useMindConnection();
  const meta = getCognitiveSourceMeta(effectiveMode);

  const badgeBg =
    meta.badgeColor === "purple"
      ? t.purpleSoft
      : meta.badgeColor === "blue"
        ? t.blueSoft
        : meta.badgeColor === "orange"
          ? t.orangeSoft
          : t.orangeSoft;

  const badgeFg =
    meta.badgeColor === "purple"
      ? t.purple
      : meta.badgeColor === "blue"
        ? t.blue
        : meta.badgeColor === "orange"
          ? t.orange
          : t.red;

  return (
    <div
      className="rounded-xl border px-4 py-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2"
      style={{
        borderColor: meta.isExample ? t.purple : meta.isLive ? t.blue : t.orange,
        backgroundColor: meta.isExample ? `${t.purpleSoft}` : meta.isLive ? t.blueSoft : t.orangeSoft,
      }}
    >
      <div className="min-w-0">
        <div className="flex items-center gap-2 flex-wrap mb-1">
          <span
            className="text-[11px] font-semibold px-2 py-0.5 rounded-full"
            style={{ backgroundColor: badgeBg, color: badgeFg }}
          >
            {meta.label}
          </span>
          {meta.isLive && generatedAt && (
            <span className="text-[10px]" style={{ color: t.textMuted }}>
              更新于 {formatGeneratedAt(generatedAt)}
              {windowSize ? ` · 窗口 ${windowSize}` : ""}
            </span>
          )}
          {meta.isExample && !isReleaseBuild && (
            <span className="text-[10px]" style={{ color: t.textLight }}>
              非真实运行
            </span>
          )}
        </div>
        <p className="text-xs leading-relaxed" style={{ color: t.textMuted }}>
          {meta.description}
        </p>
      </div>
      {onSwitchSource && (
        <button
          type="button"
          onClick={onSwitchSource}
          className="shrink-0 text-xs px-3 py-1.5 rounded-lg border"
          style={{ borderColor: t.border, color: t.text, backgroundColor: t.surface }}
        >
          切换数据源
        </button>
      )}
    </div>
  );
}
