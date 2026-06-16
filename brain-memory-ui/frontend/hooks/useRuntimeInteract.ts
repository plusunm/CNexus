"use client";

import { useMemo } from "react";
import { useMindConnection, useMindOverview } from "@/cnexus-kernel";
import { useOptionalFloatRuntimeMonitorContext } from "@/components/mind/floating/FloatRuntimeMonitorContext";
import { resolveRuntimeConnectionDisplay } from "@/lib/runtimeConnection";
import { bi, navL } from "@/lib/spine/labels";

/** Microsoft-style runtime gate — single source for disable/hint across float + main shell. */
export function useRuntimeInteract() {
  const { effectiveMode } = useMindConnection();
  const { isDemo, isLive, isWarming, isFallback, canWriteMemory } = useMindOverview();
  const monitor = useOptionalFloatRuntimeMonitorContext();

  const connection = useMemo(
    () =>
      resolveRuntimeConnectionDisplay({
        effectiveMode,
        isLive,
        isWarming,
        isDemo,
        monitorPhase: monitor?.phase ?? null,
      }),
    [effectiveMode, isDemo, isLive, isWarming, monitor?.phase],
  );

  const canChat = isDemo || connection.canUseRuntimeApi;
  const canUpload = isDemo || canWriteMemory;

  const uploadStatusHint = useMemo(() => {
    if (isDemo) return null;
    if (canUpload) return null;
    if (isFallback || effectiveMode === "fallback") return "当前为离线模式，上传需连接 Runtime";
    if (isWarming) return "Runtime 正在启动，上传暂不可用";
    if (isLive) return "认知索引构建中，上传将在完全就绪后开放";
    return bi(navL.workbenchOffline);
  }, [isDemo, canUpload, isFallback, effectiveMode, isWarming, isLive]);

  const isConnecting =
    monitor?.isChecking === true ||
    monitor?.phase === "checking" ||
    (effectiveMode === "runtime" && isWarming && !isLive);

  const statusHint = useMemo(() => {
    if (isDemo) return null;
    if (canChat) return null;
    if (isFallback || effectiveMode === "fallback") return bi(navL.workbenchOffline);
    if (isWarming || monitor?.isWarming || isConnecting) return bi(navL.workbenchWarming);
    return bi(navL.workbenchOffline);
  }, [isDemo, canChat, isFallback, effectiveMode, isWarming, monitor?.isWarming, isConnecting]);

  return {
    canChat,
    canUpload,
    canInteract: canChat,
    connection,
    statusHint,
    uploadStatusHint,
    isWarming: !isDemo && effectiveMode === "runtime" && !canChat && (isWarming || monitor?.isWarming),
    isConnecting,
    isLive,
    isDemo,
    phase: connection.phase,
  };
}
