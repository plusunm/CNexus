"use client";

import { useCallback, useState } from "react";
import { FloatingMiniDialog, floatingDialogCloseProps } from "./floating/FloatingMiniDialog";
import { useMindTheme } from "./MindUiProvider";
import {
  buildChatShareLink,
  copyChatShare,
  formatChatShareText,
  type ChatSharePayload,
} from "@/lib/chatShare";

type Props = {
  payload: ChatSharePayload;
  onClose: () => void;
};

export function ChatShareDialog({ payload, onClose }: Props) {
  const t = useMindTheme();
  const [status, setStatus] = useState<"ready" | "copying" | "copied" | "error">("ready");
  const [error, setError] = useState<string | null>(null);
  const link = buildChatShareLink(payload);

  const handleCopy = useCallback(async () => {
    setStatus("copying");
    setError(null);
    try {
      await Promise.race([
        copyChatShare(payload),
        new Promise((_, reject) => window.setTimeout(() => reject(new Error("复制超时")), 4000)),
      ]);
      setStatus("copied");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "复制失败");
    }
  }, [payload]);

  return (
    <FloatingMiniDialog
      title="分享对话"
      subtitle="复制链接或全文到剪贴板"
      onClose={onClose}
      width={360}
      placement="portal"
      contentMaxHeight={280}
    >
      <div className="space-y-3 text-xs">
        <label className="flex flex-col gap-1">
          <span style={{ color: t.textMuted }}>分享链接</span>
          <input
            readOnly
            className="w-full border rounded-lg px-2.5 py-1.5 font-mono text-[10px] box-border"
            style={{ borderColor: t.border, backgroundColor: t.surface, color: t.text }}
            value={link}
            onFocus={(e) => e.currentTarget.select()}
          />
        </label>
        <div
          className="rounded-lg px-2.5 py-2 max-h-28 overflow-y-auto cnexus-float-scroll whitespace-pre-wrap"
          style={{ backgroundColor: t.bg, border: `1px solid ${t.border}`, color: t.textMuted }}
        >
          {formatChatShareText(payload)}
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            className="flex-1 py-2 rounded-lg text-white font-medium disabled:opacity-50"
            style={{ backgroundColor: t.blue }}
            disabled={status === "copying"}
            onClick={() => void handleCopy()}
          >
            {status === "copying" ? "复制中…" : status === "copied" ? "再次复制" : "复制分享内容"}
          </button>
          <button
            type="button"
            className="px-4 py-2 rounded-lg font-medium"
            style={{ backgroundColor: t.surface, color: t.text, border: `1px solid ${t.border}` }}
            {...floatingDialogCloseProps(onClose)}
          >
            关闭
          </button>
        </div>
        {status === "copied" && (
          <p className="text-[10px]" style={{ color: t.green }}>
            已复制到剪贴板
          </p>
        )}
        {error && (
          <p className="text-[10px]" style={{ color: t.red }}>
            {error}（可手动选中上方链接复制）
          </p>
        )}
      </div>
    </FloatingMiniDialog>
  );
}
