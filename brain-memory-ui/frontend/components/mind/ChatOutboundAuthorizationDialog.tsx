"use client";

import { useMindTheme } from "./MindUiProvider";
import { FloatingMiniDialog } from "./floating/FloatingMiniDialog";

export type ChatOutboundPreview = {
  prepareId: string;
  userMessage: string;
  memoryContext: string;
  governanceInjection: string;
  systemPrompt: string;
  outboundPreview: string;
  hasInjection: boolean;
};

type Props = {
  preview: ChatOutboundPreview;
  loading?: boolean;
  onAuthorize: () => void;
  onSendUserOnly: () => void;
  onCancel: () => void;
};

export function ChatOutboundAuthorizationDialog({
  preview,
  loading = false,
  onAuthorize,
  onSendUserOnly,
  onCancel,
}: Props) {
  const t = useMindTheme();

  return (
    <FloatingMiniDialog
      title="授权发送"
      subtitle="确认注入内容，或选择仅发送你的原始消息"
      onClose={onCancel}
      width={420}
      contentMaxHeight={360}
      placement="portal"
    >
      <div className="space-y-3 text-xs">
        <p style={{ color: t.textMuted }}>
          若对下方注入内容不满意，可点「仅发送我的消息」跳过注入；点「取消」可回到输入框修改后重试。
        </p>

        <section>
          <p className="font-semibold mb-1" style={{ color: t.blue }}>
            你的消息
          </p>
          <pre
            className="whitespace-pre-wrap break-words rounded-lg p-2 cnexus-float-scroll max-h-24 overflow-y-auto"
            style={{
              color: t.text,
              backgroundColor: "rgba(255,255,255,0.04)",
              border: `1px solid ${t.border}`,
            }}
          >
            {preview.userMessage}
          </pre>
        </section>

        <section>
          <details>
            <summary className="cursor-pointer font-semibold mb-1 list-none [&::-webkit-details-marker]:hidden" style={{ color: t.orange }}>
              系统注入 · 记忆
              <span className="font-normal ml-1 opacity-75">
                {preview.memoryContext.trim() ? "（点击展开）" : "（无）"}
              </span>
            </summary>
            <pre
              className="whitespace-pre-wrap break-words rounded-lg p-2 cnexus-float-scroll max-h-28 overflow-y-auto"
              style={{
                color: t.text,
                backgroundColor: "rgba(255,255,255,0.04)",
                border: `1px solid ${t.border}`,
              }}
            >
              {preview.memoryContext.trim() || "(无)"}
            </pre>
          </details>
        </section>

        <section>
          <details>
            <summary className="cursor-pointer font-semibold mb-1 list-none [&::-webkit-details-marker]:hidden" style={{ color: t.orange }}>
              系统注入 · 治理 / 身份
              <span className="font-normal ml-1 opacity-75">
                {preview.governanceInjection.trim() ? "（点击展开）" : "（无）"}
              </span>
            </summary>
            <pre
              className="whitespace-pre-wrap break-words rounded-lg p-2 cnexus-float-scroll max-h-28 overflow-y-auto"
              style={{
                color: t.text,
                backgroundColor: "rgba(255,255,255,0.04)",
                border: `1px solid ${t.border}`,
              }}
            >
              {preview.governanceInjection.trim() || "(无)"}
            </pre>
          </details>
        </section>

        <details>
          <summary className="cursor-pointer" style={{ color: t.textMuted }}>
            查看完整 outbound 预览
          </summary>
          <pre
            className="mt-2 whitespace-pre-wrap break-words rounded-lg p-2 cnexus-float-scroll max-h-40 overflow-y-auto text-[10px]"
            style={{
              color: t.textLight,
              backgroundColor: "rgba(0,0,0,0.2)",
              border: `1px solid ${t.border}`,
              fontFamily: t.fontMono,
            }}
          >
            {preview.outboundPreview}
          </pre>
        </details>

        <div className="flex flex-col gap-2 pt-1">
          <button
            type="button"
            className="w-full px-3 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-60"
            style={{ backgroundColor: t.green }}
            disabled={loading}
            onClick={onAuthorize}
          >
            {loading ? "发送中…" : "授权并发送（含注入）"}
          </button>
          <button
            type="button"
            className="w-full px-3 py-2 rounded-lg text-sm font-medium disabled:opacity-60"
            style={{
              color: t.blue,
              border: `1px solid ${t.blue}66`,
              backgroundColor: `${t.blue}14`,
            }}
            disabled={loading}
            onClick={onSendUserOnly}
          >
            仅发送我的消息（跳过注入）
          </button>
          <button
            type="button"
            className="w-full px-3 py-2 rounded-lg text-sm font-medium disabled:opacity-60"
            style={{
              color: t.textMuted,
              border: `1px solid ${t.border}`,
              backgroundColor: "rgba(255,255,255,0.04)",
            }}
            disabled={loading}
            onClick={onCancel}
          >
            取消，回到输入框修改
          </button>
        </div>
      </div>
    </FloatingMiniDialog>
  );
}
