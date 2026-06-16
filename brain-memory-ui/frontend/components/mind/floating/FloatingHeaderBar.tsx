"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  GripHorizontal,
  Pin,
  PinOff,
  X,
} from "lucide-react";
import { CnexusAvatarIcon } from "../CnexusAvatarIcon";
import { useMindConnection } from "../MindConnectionProvider";
import { useMindOverview } from "@/cnexus-kernel";
import { floatTy } from "@/lib/floatTypography";
import { useMindTheme } from "../MindUiProvider";
import type { FloatStage } from "@/lib/floatingBarStorage";
import { useFloatRuntimeMonitorContext } from "./FloatRuntimeMonitorContext";
import { getCognitiveSourceMetaForRuntime } from "@/lib/cognitiveSource";
import { resolveRuntimeConnectionDisplay } from "@/lib/runtimeConnection";
import { isTauriDesktop } from "@/lib/tauriDesktop";
import { FloatingAppMenu, type FloatingMenuItem } from "./FloatingAppMenu";
import { FloatConnectionControl } from "./FloatConnectionControl";

type Props = {
  stage: FloatStage;
  pinned: boolean;
  badgeCount: number;
  badgeTitle?: string;
  onTogglePin: () => void;
  onExpand: () => void;
  onCollapseBar: () => void;
  onCollapseDock: () => void;
  onOpenDashboard: () => void;
  onOpenOverview: () => void;
  onHideFloat: () => void;
  onOpenConnectionPanel: () => void;
  connectionPanelOpen: boolean;
  onConnectionPanelOpenChange: (open: boolean) => void;
  onQuit: () => void;
  onOpenIntegration: (kind: "dingtalk" | "llm") => void;
  onOpenAbout: () => void;
  /** Close grip menu when a sub-dialog opens (integration / about / connection). */
  subDialogOpen?: boolean;
  onPrepareForMenu?: () => void;
  onBrandMenuOpenChange?: (open: boolean) => void;
  onDragDown: (e: React.PointerEvent<HTMLElement>) => void;
  onDragMove: (e: React.PointerEvent<HTMLElement>) => void;
  onDragUp: (e: React.PointerEvent<HTMLElement>) => void;
};

function stopDrag(e: React.PointerEvent | React.MouseEvent) {
  e.stopPropagation();
}

export function FloatingHeaderBar({
  stage,
  pinned,
  badgeCount,
  badgeTitle,
  onTogglePin,
  onExpand,
  onCollapseBar,
  onCollapseDock,
  onOpenDashboard,
  onOpenOverview,
  onHideFloat,
  onOpenConnectionPanel,
  connectionPanelOpen,
  onConnectionPanelOpenChange,
  onQuit,
  onOpenIntegration,
  onOpenAbout,
  onPrepareForMenu,
  onBrandMenuOpenChange,
  subDialogOpen = false,
  onDragDown,
  onDragMove,
  onDragUp,
}: Props) {
  const t = useMindTheme();
  const { effectiveMode } = useMindConnection();
  const { isLive, isWarming, isDemo } = useMindOverview();
  const monitor = useFloatRuntimeMonitorContext();
  const connection = resolveRuntimeConnectionDisplay({
    effectiveMode,
    isLive,
    isWarming,
    isDemo,
    monitorPhase: monitor.phase,
  });
  const meta = getCognitiveSourceMetaForRuntime({
    effectiveMode,
    isLive,
    isWarming,
    isDemo,
    monitorPhase: monitor.phase,
  });
  const gripMenuRef = useRef<HTMLButtonElement>(null);
  const [brandMenuOpen, setBrandMenuOpen] = useState(false);

  const statusColor =
    connection.phase === "live"
      ? t.green
      : connection.phase === "warming" || monitor.isChecking
        ? t.orange
        : connection.phase === "demo"
          ? t.purple
          : t.orange;
  const statusLabel =
    effectiveMode === "runtime" || effectiveMode === "fallback"
      ? `${meta.label} · ${connection.connectionLabel}`
      : meta.label;

  const closeBrandMenu = useCallback(() => {
    setBrandMenuOpen(false);
    onBrandMenuOpenChange?.(false);
  }, [onBrandMenuOpenChange]);

  const runMenuAction = useCallback(
    (action: () => void, options?: { skipPrepare?: boolean }) => {
      closeBrandMenu();
      if (!options?.skipPrepare) onPrepareForMenu?.();
      action();
    },
    [closeBrandMenu, onPrepareForMenu],
  );

  useEffect(() => {
    if (subDialogOpen) closeBrandMenu();
  }, [subDialogOpen, closeBrandMenu]);

  const brandMenuItems: FloatingMenuItem[] = [
    ...(isTauriDesktop()
      ? [{ id: "dashboard", label: "打开大屏窗口", onClick: () => runMenuAction(onOpenDashboard) }]
      : [{ id: "overview", label: "打开认知工作台", onClick: () => runMenuAction(onOpenOverview) }]),
    {
      id: "dingtalk",
      label: "钉钉通知配置",
      onClick: () => runMenuAction(() => onOpenIntegration("dingtalk")),
    },
    {
      id: "llm",
      label: "大模型 API 填写",
      onClick: () => runMenuAction(() => onOpenIntegration("llm")),
    },
    {
      id: "about",
      label: "关于我们",
      onClick: () => runMenuAction(onOpenAbout),
      separatorBefore: true,
    },
    { id: "dock", label: "收起到 Dock", onClick: () => runMenuAction(onCollapseDock, { skipPrepare: true }), separatorBefore: true },
    ...(isTauriDesktop()
      ? [
          {
            id: "hide",
            label: "隐藏悬浮条",
            onClick: () => runMenuAction(onHideFloat, { skipPrepare: true }),
            separatorBefore: true,
          },
          {
            id: "connection",
            label: "连接服务",
            onClick: () => runMenuAction(onOpenConnectionPanel),
            separatorBefore: true,
          },
          { id: "quit", label: "退出 CNexus", onClick: () => runMenuAction(onQuit, { skipPrepare: true }), danger: true },
        ]
      : []),
  ];

  const openBrandMenu = useCallback(() => {
    setBrandMenuOpen(true);
    onBrandMenuOpenChange?.(true);
  }, [onBrandMenuOpenChange]);

  const onHeaderContextMenu = useCallback(
    (e: React.MouseEvent<HTMLElement>) => {
      const target = e.target as HTMLElement;
      if (target.closest("[data-no-drag], button, a, input, select, textarea, [role='menu']")) return;
      e.preventDefault();
      openBrandMenu();
    },
    [openBrandMenu],
  );

  return (
    <>
      <div
        className="flex items-center gap-2 px-3 py-2 border-b select-none touch-none cursor-grab active:cursor-grabbing shrink-0"
      style={{
        borderColor: t.border,
        backgroundColor: "rgba(18, 24, 38, 0.6)",
      }}
      data-drag-handle
      title="拖动窗口 · 左侧六点打开菜单 · 右键菜单"
      onPointerDown={onDragDown}
      onPointerMove={onDragMove}
      onPointerUp={onDragUp}
      onContextMenu={onHeaderContextMenu}
    >
      <div className="relative shrink-0" data-no-drag>
        <button
          ref={gripMenuRef}
          type="button"
          className="p-0.5 rounded cursor-default hover:bg-white/5 transition-colors"
          style={{ color: t.textMuted }}
          title="CNexus 菜单"
          aria-haspopup="menu"
          aria-expanded={brandMenuOpen}
          onPointerDown={stopDrag}
          onClick={(e) => {
            e.stopPropagation();
            setBrandMenuOpen((open) => {
              const next = !open;
              if (next) onPrepareForMenu?.();
              onBrandMenuOpenChange?.(next);
              return next;
            });
          }}
        >
          <GripHorizontal className="w-4 h-4 opacity-60 pointer-events-none" />
        </button>
        {brandMenuOpen && (
          <FloatingAppMenu
            items={brandMenuItems}
            anchor={gripMenuRef.current?.getBoundingClientRect() ?? null}
            onClose={closeBrandMenu}
            placement={isTauriDesktop() ? "panel" : "portal"}
          />
        )}
      </div>

      <div className="flex items-center gap-1.5 min-w-0 min-h-0 flex-1">
        <CnexusAvatarIcon size={40} rounded="xl" />
        <div className="min-w-0 text-left pointer-events-none">
          <p className={`${floatTy.title} truncate`} style={{ color: t.text }}>
            CNexus
          </p>
          <p className={`${floatTy.subtitle} truncate`} style={{ color: statusColor }}>
            {statusLabel}
          </p>
        </div>
        {badgeCount > 0 && (
          <button
            type="button"
            className={`ml-1 min-w-[20px] h-5 px-1 rounded-full ${floatTy.badge} flex items-center justify-center cursor-pointer hover:brightness-110`}
            style={{ backgroundColor: t.red, color: "#fff" }}
            title={badgeTitle ? `${badgeTitle} · 点击打开连接服务` : "点击打开连接服务"}
            onPointerDown={stopDrag}
            onClick={(e) => {
              e.stopPropagation();
              onOpenConnectionPanel();
            }}
          >
            {badgeCount > 9 ? "9+" : badgeCount}
          </button>
        )}
      </div>

      <div className="flex items-center gap-0.5 shrink-0">
        <FloatConnectionControl
          open={connectionPanelOpen}
          onOpenChange={onConnectionPanelOpenChange}
          compact
        />

        <button
          type="button"
          className="p-1 rounded-md transition hover:brightness-110 cursor-pointer shrink-0"
          style={{
            color: pinned ? t.blue : t.textMuted,
            backgroundColor: pinned ? `${t.blue}22` : "rgba(255,255,255,0.04)",
            border: `1px solid ${pinned ? `${t.blue}66` : t.border}`,
          }}
          title={pinned ? "已置顶（窗口始终在最前）" : "未置顶（点击置顶）"}
          aria-pressed={pinned}
          onPointerDown={stopDrag}
          onClick={onTogglePin}
        >
          {pinned ? <Pin className="w-3.5 h-3.5" /> : <PinOff className="w-3.5 h-3.5" />}
        </button>

        {stage === "bar" && (
          <button
            type="button"
            className="p-1 rounded-md transition hover:brightness-110 cursor-pointer shrink-0"
            style={{ color: t.textMuted }}
            title="展开面板"
            onPointerDown={stopDrag}
            onClick={onExpand}
          >
            <ChevronUp className="w-4 h-4" />
          </button>
        )}
        {stage === "expanded" && (
          <button
            type="button"
            className="p-1 rounded-md transition hover:brightness-110 cursor-pointer shrink-0"
            style={{ color: t.textMuted }}
            title="收起到条"
            onPointerDown={stopDrag}
            onClick={onCollapseBar}
          >
            <ChevronDown className="w-4 h-4" />
          </button>
        )}

        <button
          type="button"
          className="p-1 rounded-md transition hover:brightness-110 cursor-pointer shrink-0"
          style={{ color: t.textMuted }}
          title="收起到 Dock"
          onPointerDown={stopDrag}
          onClick={onCollapseDock}
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
      </div>
    </>
  );
}
