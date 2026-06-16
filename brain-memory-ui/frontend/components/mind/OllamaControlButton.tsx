"use client";

import { useCallback, useState } from "react";
import { ExternalLink } from "lucide-react";
import { deriveOllamaUiPhase, useOllamaStatus } from "@/hooks/useOllamaStatus";
import { floatTy } from "@/lib/floatTypography";
import { useMindTheme } from "./MindUiProvider";
import { FloatingMiniDialog } from "./floating/FloatingMiniDialog";

function stopDrag(e: React.PointerEvent | React.MouseEvent) {
  e.stopPropagation();
}

export function OllamaControlButton({ compact = false }: { compact?: boolean }) {
  const t = useMindTheme();
  const { status, start, stop } = useOllamaStatus();
  const [helpOpen, setHelpOpen] = useState(false);
  const phase = deriveOllamaUiPhase(status);

  const color =
    phase === "running"
      ? t.green
      : phase === "stopped"
        ? t.orange
        : phase === "runtime_offline" || phase === "demo"
          ? t.textMuted
          : phase === "not_installed" || phase === "error"
            ? t.red
            : t.orange;

  const label = compact
    ? phase === "loading"
      ? "…"
      : "Ollama"
    : phase === "loading"
      ? "Ollama …"
      : phase === "running"
        ? "Ollama 运行中"
        : phase === "stopped"
          ? "Ollama 未启动"
          : phase === "runtime_offline"
            ? "Ollama 待连接"
            : phase === "demo"
              ? "Ollama Demo"
              : phase === "error"
                ? "Ollama 检测失败"
                : "Ollama 未安装";

  const title =
    status.error ??
    (phase === "running"
      ? "Ollama 服务已运行，点击可关闭"
      : phase === "stopped"
        ? `Ollama 已安装（${status.binaryPath ?? "本机"}），服务未运行，点击启动`
        : phase === "runtime_offline"
          ? "Runtime 未连接，请点悬浮窗「连接服务」"
          : phase === "demo"
            ? "请先连接 Runtime"
            : phase === "not_installed"
            ? "本机未找到 Ollama 可执行文件"
            : "正在检测 Ollama");

  const onClick = useCallback(async () => {
    if (phase === "loading") return;

    if (phase === "runtime_offline" || phase === "demo") {
      setHelpOpen(true);
      return;
    }

    if (phase === "not_installed" || phase === "error") {
      setHelpOpen(true);
      return;
    }

    if (phase === "running") {
      await stop();
      return;
    }

    if (phase === "stopped") {
      const result = await start();
      if (!result.ok && result.reason === "not_installed") {
        setHelpOpen(true);
      }
    }
  }, [phase, start, stop]);

  const helpTitle =
    phase === "stopped"
      ? "启动 Ollama"
      : phase === "runtime_offline" || phase === "demo"
        ? "连接 Runtime"
        : "安装 Ollama";

  const helpBody =
    phase === "stopped" ? (
      <>
        <p style={{ color: t.textMuted }}>
          本机已安装 Ollama，但服务尚未在 {status.host} 运行。请点击悬浮窗上的 Ollama 按钮启动，或从开始菜单打开
          Ollama。
        </p>
        {status.binaryPath && (
          <p className={`${floatTy.mono} break-all`} style={{ color: t.textLight }}>
            {status.binaryPath}
          </p>
        )}
        <button
          type="button"
          className={`w-full px-3 py-2 rounded-lg text-white ${floatTy.btn}`}
          style={{ backgroundColor: t.green }}
          onClick={() => void start().then(() => setHelpOpen(false))}
        >
          立即启动 Ollama
        </button>
      </>
    ) : phase === "runtime_offline" || phase === "demo" ? (
      <p style={{ color: t.textMuted }}>
        Ollama 状态由本机 Runtime API 检测。请先在悬浮窗标题栏点击 <b>连接服务</b> 连接 Runtime，再启动
        Ollama。
      </p>
    ) : (
      <>
        <p style={{ color: t.textMuted }}>
          未在本机找到 Ollama。若已安装仍显示此项，请确认 Runtime 已上线，并检查是否安装在默认路径。
        </p>
        <a
          href={status.downloadUrl}
          target="_blank"
          rel="noopener noreferrer"
          className={`flex items-center justify-center gap-2 px-3 py-2 rounded-lg transition hover:brightness-110 ${floatTy.btn}`}
          style={{
            backgroundColor: `${t.blue}22`,
            border: `1px solid ${t.blue}66`,
            color: t.blue,
          }}
        >
          <ExternalLink className="w-3.5 h-3.5" />
          前往 ollama.com 下载
        </a>
      </>
    );

  return (
    <>
      <button
        type="button"
        className={`inline-flex items-center gap-1 rounded-md border transition hover:brightness-110 cursor-pointer disabled:opacity-60 shrink-0 whitespace-nowrap ${
          compact ? `${floatTy.btn} px-2 py-1` : "text-[10px] font-medium px-2 py-0.5"
        }`}
        style={{
          color,
          backgroundColor: `${color}18`,
          borderColor: `${color}55`,
        }}
        title={title}
        aria-pressed={phase === "running"}
        disabled={phase === "loading"}
        onPointerDown={stopDrag}
        onClick={() => void onClick()}
      >
        <span
          className="w-1.5 h-1.5 rounded-full shrink-0"
          style={{ backgroundColor: color, boxShadow: phase === "running" ? `0 0 6px ${color}` : undefined }}
        />
        {label}
      </button>

      {helpOpen && (
        <FloatingMiniDialog
          title={helpTitle}
          subtitle="Ollama 本地模型与向量服务"
          onClose={() => setHelpOpen(false)}
          width={340}
          placement="portal"
        >
          <div className={`space-y-3 ${floatTy.body}`} style={{ color: t.text }}>
            {helpBody}
          </div>
        </FloatingMiniDialog>
      )}
    </>
  );
}
