"use client";

import { useEffect } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { floatTy } from "@/lib/floatTypography";
import { useMindTheme } from "../MindUiProvider";
import { isTauriDesktop } from "@/lib/tauriDesktop";

type Props = {
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: React.ReactNode;
  width?: number;
  /** panel = absolute within relative parent; portal = document body fixed */
  placement?: "portal" | "panel";
  /** Max height for scrollable body; omit to size to content */
  contentMaxHeight?: number;
};

const FLOAT_DIALOG_Z = 2147483646;
const FLOAT_DIALOG_CONTENT_Z = 2147483647;

function invokeClose(onClose: () => void, e: React.SyntheticEvent) {
  e.preventDefault();
  e.stopPropagation();
  onClose();
}

export function FloatingMiniDialog({
  title,
  subtitle,
  onClose,
  children,
  width = 320,
  placement,
  contentMaxHeight,
}: Props) {
  const t = useMindTheme();
  const resolvedPlacement = placement ?? (isTauriDesktop() ? "panel" : "portal");

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    const onHide = () => onClose();
    window.addEventListener("keydown", onKey);
    window.addEventListener("pagehide", onHide);
    window.addEventListener("beforeunload", onHide);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("pagehide", onHide);
      window.removeEventListener("beforeunload", onHide);
    };
  }, [onClose]);

  useEffect(() => {
    if (!isTauriDesktop()) return;
    void import("@tauri-apps/api/window").then(({ getCurrentWindow }) => {
      const win = getCurrentWindow();
      void win.setIgnoreCursorEvents(false);
      void win.setFocus();
    });
  }, []);

  const overlayClass =
    resolvedPlacement === "panel"
      ? "absolute inset-0 flex items-center justify-center p-3"
      : "fixed inset-0 flex items-center justify-center p-4";

  const overlay = (
    <div
      className={overlayClass}
      style={{
        zIndex: FLOAT_DIALOG_Z,
        backgroundColor: "rgba(6, 9, 18, 0.62)",
        pointerEvents: "auto",
      }}
      data-cnexus-overlay
      data-no-drag
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="w-full rounded-xl shadow-2xl overflow-hidden"
        style={{
          maxWidth: width,
          backgroundColor: t.bg,
          border: `1px solid ${t.border}`,
          pointerEvents: "auto",
          position: "relative",
          zIndex: FLOAT_DIALOG_CONTENT_Z,
        }}
        onClick={(e) => e.stopPropagation()}
        onPointerDown={(e) => e.stopPropagation()}
      >
        <div
          className="flex items-start justify-between gap-2 px-3 py-2.5 border-b"
          style={{ borderColor: t.border, backgroundColor: "rgba(18,24,38,0.6)" }}
        >
          <div className="min-w-0">
            <p className={`${floatTy.title} truncate`} style={{ color: t.text }}>
              {title}
            </p>
            {subtitle && (
              <p className={`${floatTy.caption} mt-0.5 truncate`} style={{ color: t.textMuted }}>
                {subtitle}
              </p>
            )}
          </div>
          <button
            type="button"
            className="p-1 rounded-md shrink-0 hover:brightness-125"
            style={{ color: t.textMuted, pointerEvents: "auto" }}
            onPointerDown={(e) => invokeClose(onClose, e)}
            onClick={(e) => invokeClose(onClose, e)}
            aria-label="关闭"
          >
            <X className="w-4 h-4 pointer-events-none" />
          </button>
        </div>
        <div
          className={`p-3 overflow-y-auto cnexus-float-scroll ${floatTy.body}`}
          style={
            contentMaxHeight != null
              ? { maxHeight: contentMaxHeight }
              : { maxHeight: "none" }
          }
        >
          {children}
        </div>
      </div>
    </div>
  );

  if (resolvedPlacement === "panel") return overlay;
  if (typeof document === "undefined") return null;
  return createPortal(overlay, document.body);
}

export function floatingDialogCloseProps(onClose: () => void) {
  return {
    onPointerDown: (e: React.PointerEvent) => invokeClose(onClose, e),
    onClick: (e: React.MouseEvent) => invokeClose(onClose, e),
  };
}
