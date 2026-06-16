"use client";

import { useEffect } from "react";
import { useFloatingBarStore } from "@/lib/floatingBarStore";
import {
  hideTauriFloatWindow,
  initTauriDesktop,
  isTauriDesktop,
  listenDashboardOpened,
  listenFloatRevealed,
  listenTauriFloatToggle,
  revealTauriFloatWindow,
  syncTauriFloatWindow,
} from "@/lib/tauriDesktop";

/** Sync float stage → Tauri window size + global shortcut events. */
export function useTauriDesktopSync() {
  const stage = useFloatingBarStore((s) => s.stage);
  const pinned = useFloatingBarStore((s) => s.pinned);
  const uiModalOpen = useFloatingBarStore((s) => s.uiModalOpen);
  const setStage = useFloatingBarStore((s) => s.setStage);
  const setPinned = useFloatingBarStore((s) => s.setPinned);
  const collapseToDock = useFloatingBarStore((s) => s.collapseToDock);

  useEffect(() => {
    if (!isTauriDesktop()) return;
    void initTauriDesktop();
  }, []);

  useEffect(() => {
    if (!isTauriDesktop()) return;
    const effectiveStage = uiModalOpen ? "expanded" : stage;
    void syncTauriFloatWindow(effectiveStage, pinned);
  }, [stage, pinned, uiModalOpen]);

  useEffect(() => {
    if (!isTauriDesktop()) return;
    let unlisten: (() => void) | undefined;
    void listenFloatRevealed(() => {
      const { stage: s, pinned: p } = useFloatingBarStore.getState();
      void syncTauriFloatWindow(s, p);
    }).then((fn) => {
      unlisten = fn;
    });
    return () => unlisten?.();
  }, []);

  useEffect(() => {
    if (!isTauriDesktop()) return;
    let unlisten: (() => void) | undefined;
    void listenDashboardOpened(() => {
      setPinned(false);
    }).then((fn) => {
      unlisten = fn;
    });
    return () => unlisten?.();
  }, [setPinned]);

  useEffect(() => {
    if (!isTauriDesktop()) return;
    let unlisten: (() => void) | undefined;
    void listenTauriFloatToggle(async () => {
      const { getCurrentWindow } = await import("@tauri-apps/api/window");
      const visible = await getCurrentWindow().isVisible();
      const currentStage = useFloatingBarStore.getState().stage;

      if (!visible) {
        await revealTauriFloatWindow();
        const { stage: s, pinned: p } = useFloatingBarStore.getState();
        void syncTauriFloatWindow(s, p);
        return;
      }

      if (currentStage === "expanded") {
        useFloatingBarStore.getState().collapseToBar();
        return;
      }
      if (currentStage === "bar") {
        collapseToDock();
        return;
      }
      await hideTauriFloatWindow();
    }).then((fn) => {
      unlisten = fn;
    });
    return () => unlisten?.();
  }, [collapseToDock]);
}
