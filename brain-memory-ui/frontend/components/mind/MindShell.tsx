"use client";

import { useEffect } from "react";
import { useMindConnection } from "@/cnexus-kernel";
import { ConnectionModeGate } from "./ConnectionModeGate";
import { useMindUi } from "./MindUiProvider";
import { FloatingMindBar } from "./floating/FloatingMindBar";
import OverviewMindLayout from "./OverviewMindLayout";
import CognitiveMindLayout from "./cognitive/CognitiveMindLayout";
import type { ShellLayout, ShellPanel } from "@/cnexus-kernel/shellTypes";
import { panelDomId } from "@/cnexus-kernel/shellTypes";
import { useFloatingBarStore } from "@/lib/floatingBarStore";
import { FLOAT_SHORTCUT_HINT_TAURI, FLOAT_SHORTCUT_HINT_WEB } from "@/lib/floatWindowSpec";
import { isTauriDesktop } from "@/lib/tauriDesktop";

export type MindShellProps = {
  layout?: ShellLayout;
  panel?: ShellPanel | null;
  desktop?: boolean;
};

/** Pure layout composer — no fetch, no WS, no overview merge. */
export function MindShell({
  layout: layoutProp = "overview",
  panel = null,
  desktop = false,
}: MindShellProps) {
  const { preference, selectPreference, hydrated } = useMindConnection();
  const { mode: uiMode, theme, setMode: setUiMode } = useMindUi();
  const openPanel = useFloatingBarStore((s) => s.openPanel);
  const setStage = useFloatingBarStore((s) => s.setStage);

  useEffect(() => {
    if (desktop) return;
    if (layoutProp !== uiMode) setUiMode(layoutProp);
  }, [layoutProp, uiMode, setUiMode, desktop]);

  useEffect(() => {
    if (!panel || !preference) return;
    const activeLayout = desktop ? "float" : layoutProp;

    if (activeLayout === "float") {
      openPanel(panel);
      return;
    }

    const id = panelDomId(panel);
    window.requestAnimationFrame(() => {
      document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }, [panel, preference, layoutProp, desktop, openPanel]);

  useEffect(() => {
    if (desktop) {
      setUiMode("float");
    }
  }, [desktop, setUiMode]);

  useEffect(() => {
    if (!desktop || !hydrated || preference) return;
    selectPreference("runtime");
  }, [desktop, hydrated, preference, selectPreference]);

  if (!preference) {
    if (desktop) {
      return (
        <div className="w-full h-full min-h-0 overflow-hidden bg-transparent flex flex-col">
          <ConnectionModeGate compact />
        </div>
      );
    }
    return <ConnectionModeGate compact={false} />;
  }

  const layout = desktop ? "float" : uiMode;

  if (layout === "float") {
    return (
      <div
        className={
          desktop
            ? "w-full h-full min-h-0 overflow-hidden bg-transparent flex flex-col"
            : "min-h-screen relative overflow-hidden"
        }
        style={
          desktop
            ? undefined
            : {
                background:
                  "radial-gradient(ellipse at 80% 90%, rgba(47,107,255,0.08), transparent 50%), radial-gradient(ellipse at 10% 10%, rgba(138,92,255,0.06), transparent 45%), #060912",
                color: theme.text,
                fontFamily: theme.fontSans,
              }
        }
        data-ui-mode="float"
        data-connection-mode={preference}
      >
        {!desktop && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center opacity-30">
            <p className="text-sm" style={{ color: theme.textMuted }}>
              悬浮模式 · {isTauriDesktop() ? FLOAT_SHORTCUT_HINT_TAURI : FLOAT_SHORTCUT_HINT_WEB}
            </p>
          </div>
        )}
        <FloatingMindBar desktop={desktop} />
      </div>
    );
  }

  return (
    <div
      className="min-h-screen"
      style={{
        backgroundColor: theme.bg,
        color: theme.text,
        fontFamily: theme.fontSans,
      }}
      data-ui-mode={layout}
      data-connection-mode={preference}
    >
      {layout === "cognitive" ? <CognitiveMindLayout /> : <OverviewMindLayout />}
    </div>
  );
}

export default MindShell;
