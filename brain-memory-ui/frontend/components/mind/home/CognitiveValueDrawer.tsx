"use client";

import { X } from "lucide-react";
import type { ValueDetail } from "@/lib/cognitiveValue";
import { useMindTheme } from "../MindUiProvider";

type Props = {
  detail: ValueDetail | null;
  narrative?: string;
  onClose: () => void;
};

export function CognitiveValueDrawer({ detail, narrative, onClose }: Props) {
  const t = useMindTheme();
  if (!detail && !narrative) return null;

  const title =
    detail?.kind === "insight"
      ? detail.item.title
      : detail?.kind === "discovery"
        ? detail.item.title
        : detail?.label ?? "思考详情";

  const body =
    detail?.kind === "insight"
      ? detail.item.description
      : detail?.kind === "discovery"
        ? detail.item.description
        : detail?.kind === "text"
          ? detail.item.text
          : "";

  const why =
    detail?.kind === "insight"
      ? detail.item.why
      : detail?.kind === "discovery"
        ? detail.item.why
        : "";

  const evidence =
    detail?.kind === "insight"
      ? detail.item.evidence ?? []
      : detail?.kind === "discovery"
        ? detail.item.evidence ?? []
        : [];

  const confidence =
    detail?.kind === "insight"
      ? detail.item.confidence
      : detail?.kind === "discovery"
        ? detail.item.confidence
        : detail?.kind === "text"
          ? detail.item.confidence
          : 0;

  const novelty =
    detail?.kind === "insight"
      ? detail.item.novelty
      : detail?.kind === "discovery"
        ? detail.item.novelty
        : 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4"
      style={{ backgroundColor: "rgba(7,11,20,0.65)" }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-2xl border p-5 max-h-[80vh] overflow-auto"
        style={{ borderColor: t.border, backgroundColor: t.surface }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 mb-4">
          <div>
            <p className="text-xs font-medium mb-1" style={{ color: t.purple }}>
              完整思考
            </p>
            <h3 className="text-lg font-semibold" style={{ color: t.text }}>
              {title}
            </h3>
          </div>
          <button type="button" onClick={onClose} className="p-1 rounded-lg" style={{ color: t.textMuted }}>
            <X className="w-5 h-5" />
          </button>
        </div>

        {narrative && (
          <div
            className="rounded-xl p-3 mb-4 text-sm leading-relaxed"
            style={{ backgroundColor: t.chatBg, color: t.text, borderLeft: `3px solid ${t.blue}` }}
          >
            <span style={{ color: t.blue }}>价值总结 · </span>
            {narrative}
          </div>
        )}

        {body && (
          <p className="text-sm leading-relaxed mb-4" style={{ color: t.textMuted }}>
            {body}
          </p>
        )}

        {detail && (
          <div className="flex flex-wrap gap-2 mb-4">
            <span className="text-[11px] px-2 py-0.5 rounded-full" style={{ backgroundColor: t.purpleSoft, color: t.purple }}>
              把握度 {Math.round(confidence * 100)}%
            </span>
            {(novelty ?? 0) >= 0.65 && (
              <span className="text-[11px] px-2 py-0.5 rounded-full" style={{ backgroundColor: t.orangeSoft, color: t.orange }}>
                首次发现
              </span>
            )}
          </div>
        )}

        {why && (
          <div className="rounded-xl p-3 mb-4 text-sm" style={{ backgroundColor: t.chatBg, color: t.textMuted }}>
            <span style={{ color: t.purple }}>为什么 · </span>
            {why}
          </div>
        )}

        {evidence.length > 0 && (
          <div>
            <p className="text-[10px] uppercase tracking-wider mb-2" style={{ color: t.textLight }}>
              依据
            </p>
            <ul className="space-y-2">
              {evidence.map((line, i) => (
                <li
                  key={i}
                  className="text-xs px-3 py-2 rounded-lg border"
                  style={{ borderColor: t.border, color: t.text }}
                >
                  {line}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
