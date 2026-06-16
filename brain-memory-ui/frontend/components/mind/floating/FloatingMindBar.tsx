"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CnexusAvatarIcon } from "../CnexusAvatarIcon";
import { useMindOverview } from "@/cnexus-kernel";
import { useMindConnection } from "../MindConnectionProvider";
import { useMindTheme } from "../MindUiProvider";
import { FLOAT_TYPE_ROOT, floatTy } from "@/lib/floatTypography";
import { useFloatingBarStore } from "@/lib/floatingBarStore";
import { useRuntimeInteract } from "@/hooks/useRuntimeInteract";
import { loadFloatPanel, type FloatPanel } from "@/lib/floatingBarStorage";
import {
  clampFloatPosition,
  floatShellHeight,
  floatShellWidth,
  FLOAT_LAYOUT,
  snapFloatPosition,
} from "@/lib/floatWindowSpec";
import { FloatingHeaderBar } from "./FloatingHeaderBar";
import { FloatRuntimeMonitorProvider } from "./FloatRuntimeMonitorContext";
import { FloatingQuickButtons } from "./FloatingQuickButtons";
import { FloatingExpandPanel } from "./FloatingExpandPanel";
import { FloatingAppMenu, type FloatingMenuItem } from "./FloatingAppMenu";
import { FloatingAboutDialog } from "./FloatingAboutDialog";
import { FloatingIntegrationDialogs } from "./FloatingIntegrationDialogs";
import {
  hideTauriFloatWindow,
  initTauriDesktop,
  isTauriDesktop,
  listenFloatRevealed,
  listenTauriOpenSettings,
  openTauriDashboard,
  quitTauriApp,
  startTauriWindowDrag,
} from "@/lib/tauriDesktop";

const DOCK_SIZE = FLOAT_LAYOUT.dock.width;

function shellSizeForStage(stage: "dock" | "bar" | "expanded") {
  return {
    width: floatShellWidth(stage),
    height: floatShellHeight(stage),
  };
}

export function FloatingMindBar({ desktop = false }: { desktop?: boolean }) {
  const t = useMindTheme();
  const { effectiveMode } = useMindConnection();
  const { signals, isDemo, isLive, runtimeLogs } = useMindOverview();
  const runtimeInteract = useRuntimeInteract();
  const {
    hydrated,
    stage,
    position,
    activePanel,
    pinned,
    hydrate,
    setStage,
    setPosition,
    togglePinned,
    openPanel,
    collapseToBar,
    collapseToDock,
    bumpSession,
    setPinned,
    setUiModalOpen,
  } = useFloatingBarStore();

  const dragOrigin = useRef<{ x: number; y: number; px: number; py: number } | null>(null);
  const dockDragOrigin = useRef<{ x: number; y: number; px: number; py: number; pointerId: number; el: HTMLElement } | null>(null);
  const dockPointerRef = useRef<{ x: number; y: number; moved: boolean } | null>(null);
  const [dockMenuPos, setDockMenuPos] = useState<{ x: number; y: number } | null>(null);
  const [integrationDialog, setIntegrationDialog] = useState<null | "dingtalk" | "llm">(null);
  const [aboutOpen, setAboutOpen] = useState(false);
  const [connectionPanelOpen, setConnectionPanelOpen] = useState(false);
  const [menuBusyId, setMenuBusyId] = useState<string | null>(null);
  const [floatExposed, setFloatExposed] = useState(true);
  const prevEffectiveModeRef = useRef(effectiveMode);

  const shellSize = shellSizeForStage(stage === "dock" ? "dock" : stage === "expanded" ? "expanded" : "bar");

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (desktop || isTauriDesktop()) void initTauriDesktop();
  }, [desktop]);

  useEffect(() => {
    if (!isTauriDesktop()) return;
    let unlisten: (() => void) | undefined;
    void listenFloatRevealed(() => setFloatExposed(true)).then((fn) => {
      unlisten = fn;
    });
    return () => unlisten?.();
  }, []);

  useEffect(() => {
    const onVisibility = () => {
      setFloatExposed(document.visibilityState === "visible");
    };
    document.addEventListener("visibilitychange", onVisibility);
    onVisibility();
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, []);

  const isMonitorExposed = stage !== "dock" && floatExposed;

  const handleExpand = useCallback(() => {
    const panel = activePanel ?? loadFloatPanel() ?? "chat";
    openPanel(panel);
  }, [activePanel, openPanel]);

  const prepareFloatForMenu = useCallback(() => {
    if (stage === "dock") {
      setStage("bar");
      return;
    }
    if (stage === "bar") {
      handleExpand();
    }
  }, [stage, setStage, handleExpand]);

  const openIntegrationDialog = useCallback((kind: "dingtalk" | "llm") => {
    prepareFloatForMenu();
    setIntegrationDialog(kind);
  }, [prepareFloatForMenu]);

  const openAboutDialog = useCallback(() => {
    prepareFloatForMenu();
    setAboutOpen(true);
  }, [prepareFloatForMenu]);

  const openConnectionPanel = useCallback(() => {
    prepareFloatForMenu();
    setConnectionPanelOpen(true);
  }, [prepareFloatForMenu]);

  useEffect(() => {
    setUiModalOpen(Boolean(integrationDialog || aboutOpen || dockMenuPos || connectionPanelOpen));
  }, [integrationDialog, aboutOpen, dockMenuPos, connectionPanelOpen, setUiModalOpen]);

  useEffect(() => {
    if (!isTauriDesktop()) return;
    let unlisten: (() => void) | undefined;
    void listenTauriOpenSettings(() => openConnectionPanel()).then((fn) => {
      unlisten = fn;
    });
    return () => unlisten?.();
  }, [openConnectionPanel]);

  useEffect(() => {
    if (prevEffectiveModeRef.current === effectiveMode) return;
    prevEffectiveModeRef.current = effectiveMode;
    bumpSession();
  }, [effectiveMode, bumpSession]);

  useEffect(() => {
    if (desktop || isTauriDesktop()) return;
    const onResize = () => {
      const { width, height } = shellSizeForStage(stage === "dock" ? "dock" : stage === "expanded" ? "expanded" : "bar");
      setPosition(clampFloatPosition(position.x, position.y, width, height));
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [desktop, position.x, position.y, stage, setPosition]);

  const badgeBreakdown = useMemo(() => {
    const parts: string[] = [];
    if (signals.conflict.count > 0) parts.push(`冲突 ${signals.conflict.count}`);
    if (!isDemo && !isLive) parts.push("Runtime 未连接");
    const lastLog = runtimeLogs[runtimeLogs.length - 1];
    if (lastLog?.level === "error") parts.push("运行错误");
    return parts;
  }, [signals.conflict.count, isDemo, isLive, runtimeLogs]);

  const badgeCount = useMemo(() => {
    const conflicts = signals.conflict.count;
    const offline = !isDemo && !isLive ? 1 : 0;
    const logHint = runtimeLogs.length > 0 && runtimeLogs[runtimeLogs.length - 1]?.level === "error" ? 1 : 0;
    return conflicts + offline + logHint;
  }, [signals.conflict.count, isDemo, isLive, runtimeLogs]);

  const badgeTitle = badgeBreakdown.length > 0 ? badgeBreakdown.join(" · ") : undefined;

  const toggleVisibility = useCallback(() => {
    if (stage === "expanded") collapseToBar();
    else if (stage === "bar") collapseToDock();
    else setStage("bar");
  }, [stage, setStage, collapseToBar, collapseToDock]);

  useEffect(() => {
    if (desktop || isTauriDesktop()) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.altKey && e.shiftKey && e.key.toLowerCase() === "m") {
        e.preventDefault();
        toggleVisibility();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [toggleVisibility, desktop]);

  const commitWebPosition = useCallback(
    (x: number, y: number, width: number, height: number) => {
      const clamped = clampFloatPosition(x, y, width, height);
      setPosition(snapFloatPosition(clamped, width, height));
    },
    [setPosition],
  );

  const onDragDown = useCallback(
    (e: React.PointerEvent<HTMLElement>) => {
      if (e.button !== 0) return;
      const target = e.target as HTMLElement;
      if (target.closest("[data-no-drag], button, a, input, select, textarea, [role='menu']")) {
        return;
      }
      if (desktop || isTauriDesktop()) {
        startTauriWindowDrag();
        return;
      }
      dragOrigin.current = {
        x: e.clientX,
        y: e.clientY,
        px: position.x,
        py: position.y,
      };
      e.currentTarget.setPointerCapture(e.pointerId);
    },
    [position.x, position.y, desktop],
  );

  const onDragMove = useCallback(
    (e: React.PointerEvent<HTMLElement>) => {
      if (desktop || isTauriDesktop()) return;
      const d = dragOrigin.current;
      if (!d) return;
      commitWebPosition(
        d.px + (e.clientX - d.x),
        d.py + (e.clientY - d.y),
        shellSize.width,
        shellSize.height,
      );
    },
    [shellSize.width, shellSize.height, commitWebPosition, desktop],
  );

  const onDragUp = useCallback(
    (e: React.PointerEvent<HTMLElement>) => {
      if (!dragOrigin.current) return;
      dragOrigin.current = null;
      e.currentTarget.releasePointerCapture(e.pointerId);
      if (desktop || isTauriDesktop()) return;
      commitWebPosition(position.x, position.y, shellSize.width, shellSize.height);
    },
    [commitWebPosition, position.x, position.y, shellSize.width, shellSize.height, desktop],
  );

  const handleQuickSelect = (panel: FloatPanel) => {
    if (stage === "expanded" && activePanel === panel) {
      collapseToBar();
      return;
    }
    openPanel(panel);
  };

  const handleOpenDashboard = useCallback(() => {
    setPinned(false);
    void openTauriDashboard();
  }, [setPinned]);

  const handleOpenOverview = useCallback(() => {
    if (typeof window === "undefined") return;
    const url = `${window.location.origin}/shell?layout=overview`;
    window.open(url, "_blank", "noopener,noreferrer");
  }, []);

  const handleHideFloat = useCallback(() => {
    setFloatExposed(false);
    if (isTauriDesktop()) {
      void hideTauriFloatWindow();
      return;
    }
    collapseToDock();
  }, [collapseToDock]);

  const handleQuit = useCallback(() => {
    void quitTauriApp();
  }, []);

  const runMenuAction = useCallback(async (id: string, action: () => void | Promise<void>) => {
    setMenuBusyId(id);
    try {
      await action();
    } finally {
      setMenuBusyId(null);
    }
  }, []);

  const dockMenuItems: FloatingMenuItem[] = useMemo(() => {
    const items: FloatingMenuItem[] = [
      { id: "restore", label: "显示悬浮条", onClick: () => setStage("bar") },
      {
        id: "llm",
        label: "大模型 API 填写",
        onClick: () => openIntegrationDialog("llm"),
      },
    ];
    if (isTauriDesktop()) {
      items.push(
        {
          id: "dashboard",
          label: "打开大屏窗口",
          onClick: () => runMenuAction("dashboard", () => openTauriDashboard()),
        },
        {
          id: "hide",
          label: "隐藏到托盘",
          onClick: () => runMenuAction("hide", () => hideTauriFloatWindow()),
          separatorBefore: true,
        },
        {
          id: "connection",
          label: "连接服务",
          onClick: () => openConnectionPanel(),
        },
        {
          id: "quit",
          label: "退出 CNexus",
          onClick: () => runMenuAction("quit", () => quitTauriApp()),
          danger: true,
          separatorBefore: true,
        },
      );
    } else {
      items.push({
        id: "overview",
        label: "打开认知工作台",
        onClick: () => runMenuAction("overview", handleOpenOverview),
        separatorBefore: true,
      });
    }
    return items;
  }, [setStage, handleOpenOverview, openIntegrationDialog, openConnectionPanel, runMenuAction]);

  const onDockPointerDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (e.button !== 0) return;
      if (desktop || isTauriDesktop()) {
        dockPointerRef.current = { x: e.clientX, y: e.clientY, moved: false };
        return;
      }
      dockPointerRef.current = { x: e.clientX, y: e.clientY, moved: false };
      dockDragOrigin.current = {
        x: e.clientX,
        y: e.clientY,
        px: position.x,
        py: position.y,
        pointerId: e.pointerId,
        el: e.currentTarget,
      };
    },
    [desktop, position.x, position.y],
  );

  const onDockPointerMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      const d = dockPointerRef.current;
      if (!d) return;

      if (desktop || isTauriDesktop()) {
        if (d.moved) return;
        if (Math.abs(e.clientX - d.x) > 4 || Math.abs(e.clientY - d.y) > 4) {
          d.moved = true;
          startTauriWindowDrag();
        }
        return;
      }

      const drag = dockDragOrigin.current;
      if (!drag || d.moved) return;
      if (Math.abs(e.clientX - d.x) > 4 || Math.abs(e.clientY - d.y) > 4) {
        d.moved = true;
        drag.el.setPointerCapture(drag.pointerId);
      }
      if (d.moved && drag) {
        commitWebPosition(
          drag.px + (e.clientX - drag.x),
          drag.py + (e.clientY - drag.y),
          DOCK_SIZE,
          DOCK_SIZE,
        );
      }
    },
    [desktop, commitWebPosition],
  );

  const onDockPointerUp = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      const d = dockPointerRef.current;
      const drag = dockDragOrigin.current;
      dockPointerRef.current = null;
      dockDragOrigin.current = null;
      if (!d || e.button !== 0) return;
      if (d.moved) {
        if (drag && !desktop && !isTauriDesktop()) {
          drag.el.releasePointerCapture(drag.pointerId);
          commitWebPosition(position.x, position.y, DOCK_SIZE, DOCK_SIZE);
        }
        return;
      }
      setStage("bar");
    },
    [setStage, desktop, commitWebPosition, position.x, position.y],
  );

  const onDockContextMenu = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDockMenuPos({ x: e.clientX, y: e.clientY });
  }, []);

  if (!hydrated) return null;

  const floatOverlayDialogs = (
    <>
      {integrationDialog && (
        <FloatingIntegrationDialogs
          kind={integrationDialog}
          isDemo={isDemo}
          onClose={() => setIntegrationDialog(null)}
        />
      )}
      {aboutOpen && <FloatingAboutDialog onClose={() => setAboutOpen(false)} />}
    </>
  );

  const webShellHeight = desktop ? undefined : shellSize.height;

  const shellStyle: React.CSSProperties = desktop
    ? {
        position: "relative",
        width: "100%",
        height: "100%",
        minHeight: 0,
        fontFamily: t.fontSans,
        transition: "box-shadow 0.22s ease",
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
      }
    : {
        position: "fixed",
        left: position.x,
        top: position.y,
        zIndex: pinned ? 9999 : 9000,
        width: stage === "dock" ? DOCK_SIZE : shellSize.width,
        height: webShellHeight,
        maxHeight: webShellHeight,
        fontFamily: t.fontSans,
        transition: "width 0.22s ease, height 0.22s ease, box-shadow 0.22s ease, transform 0.22s ease",
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
      };

  if (stage === "dock") {
    return (
      <div
        className="relative touch-none select-none"
        style={{
          width: desktop ? "100%" : DOCK_SIZE,
          height: desktop ? "100%" : DOCK_SIZE,
        }}
      >
        <div
          className="rounded-2xl flex items-center justify-center cnexus-float-dock cnexus-float-type relative touch-none select-none overflow-hidden"
          style={{
            ...shellStyle,
            height: desktop ? "100%" : DOCK_SIZE,
            width: desktop ? "100%" : DOCK_SIZE,
            maxHeight: desktop ? undefined : DOCK_SIZE,
            background: "transparent",
            border: "none",
            boxShadow: pinned ? t.goalGlow : "0 10px 36px rgba(47, 107, 255, 0.45)",
            cursor: "default",
          }}
          title="左键展开 · 右键菜单 · 拖动移动"
          onPointerDown={onDockPointerDown}
          onPointerMove={onDockPointerMove}
          onPointerUp={onDockPointerUp}
          onContextMenu={onDockContextMenu}
        >
          <CnexusAvatarIcon size={DOCK_SIZE} rounded="2xl" sparkleScale={0.46} withShadow={false} />
          {badgeCount > 0 && (
            <span
              className={`absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full ${floatTy.badge} text-white pointer-events-none`}
              style={{ backgroundColor: t.red }}
              title={badgeTitle}
            >
              {badgeCount > 9 ? "9+" : badgeCount}
            </span>
          )}
        </div>
        {dockMenuPos && (
          <FloatingAppMenu
            items={dockMenuItems}
            position={dockMenuPos}
            busyId={menuBusyId}
            onClose={() => setDockMenuPos(null)}
          />
        )}
        {floatOverlayDialogs}
      </div>
    );
  }

  return (
    <FloatRuntimeMonitorProvider isExposed={isMonitorExposed} boost={connectionPanelOpen}>
    <div
      className={`rounded-2xl shadow-2xl cnexus-float-bar ${FLOAT_TYPE_ROOT} relative h-full min-h-0 overflow-hidden ${
        stage === "expanded" ? "cnexus-float-shell-expanded" : "cnexus-float-bar-stage flex flex-col"
      }`}
      style={{
        ...shellStyle,
        backgroundColor: t.bg,
        border: `1px solid ${t.border}`,
        boxShadow: pinned
          ? `${t.goalGlow}, 0 12px 40px rgba(0,0,0,0.45)`
          : "0 12px 40px rgba(0,0,0,0.35)",
      }}
      data-stage={stage}
    >
      <FloatingHeaderBar
        stage={stage}
        pinned={pinned}
        badgeCount={badgeCount}
        badgeTitle={badgeTitle}
        onTogglePin={togglePinned}
        onExpand={handleExpand}
        onCollapseBar={collapseToBar}
        onCollapseDock={collapseToDock}
        onOpenDashboard={handleOpenDashboard}
        onOpenOverview={handleOpenOverview}
        onHideFloat={handleHideFloat}
        onOpenConnectionPanel={openConnectionPanel}
        connectionPanelOpen={connectionPanelOpen}
        onConnectionPanelOpenChange={setConnectionPanelOpen}
        onQuit={handleQuit}
        onOpenIntegration={openIntegrationDialog}
        onOpenAbout={openAboutDialog}
        onPrepareForMenu={prepareFloatForMenu}
        subDialogOpen={Boolean(integrationDialog || aboutOpen || connectionPanelOpen)}
        onDragDown={onDragDown}
        onDragMove={onDragMove}
        onDragUp={onDragUp}
      />

      <FloatingQuickButtons
        activePanel={activePanel}
        onSelect={handleQuickSelect}
        canChat={runtimeInteract.canChat}
        canUpload={runtimeInteract.canUpload}
        statusHint={
          !runtimeInteract.canChat
            ? runtimeInteract.statusHint
            : runtimeInteract.uploadStatusHint
        }
      />

      {stage === "expanded" && activePanel && (
        <FloatingExpandPanel panel={activePanel} />
      )}
      {floatOverlayDialogs}
    </div>
    </FloatRuntimeMonitorProvider>
  );
}
