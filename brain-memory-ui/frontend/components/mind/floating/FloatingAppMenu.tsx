"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import { createPortal } from "react-dom";
import { floatTy } from "@/lib/floatTypography";
import { useMindTheme } from "../MindUiProvider";
import { isTauriDesktop } from "@/lib/tauriDesktop";

export type FloatingMenuItem = {
  id: string;
  label: string;
  onClick: () => void | Promise<void>;
  danger?: boolean;
  separatorBefore?: boolean;
  disabled?: boolean;
};

type Props = {
  items: FloatingMenuItem[];
  anchor?: DOMRect | null;
  position?: { x: number; y: number };
  onClose: () => void;
  /** panel = in-place absolute (Tauri float); portal = document body fixed */
  placement?: "portal" | "panel";
  busyId?: string | null;
};

type MenuLayout = {
  maxHeight: number;
  openAbove: boolean;
  left: number;
  top?: number;
  bottom?: number;
  needsScroll: boolean;
};

const MENU_GAP = 6;
const VIEWPORT_MARGIN = 8;

function computeMenuLayout(
  anchor: DOMRect | null | undefined,
  position: { x: number; y: number } | undefined,
  contentHeight: number,
): MenuLayout {
  const viewportH = window.innerHeight;
  const viewportW = window.innerWidth;
  const content = Math.max(1, Math.ceil(contentHeight));

  if (anchor) {
    const spaceBelow = viewportH - anchor.bottom - VIEWPORT_MARGIN;
    const spaceAbove = anchor.top - VIEWPORT_MARGIN;
    const openAbove = spaceBelow < content && spaceAbove > spaceBelow;
    const available = Math.max(0, (openAbove ? spaceAbove : spaceBelow) - MENU_GAP);
    const maxHeight = Math.min(content, available);
    return {
      maxHeight,
      openAbove,
      left: Math.min(anchor.left, viewportW - 168),
      top: openAbove ? undefined : anchor.bottom + MENU_GAP,
      bottom: openAbove ? viewportH - anchor.top + MENU_GAP : undefined,
      needsScroll: content > available,
    };
  }

  const x = position?.x ?? 0;
  const y = position?.y ?? 0;
  const spaceBelow = viewportH - y - VIEWPORT_MARGIN;
  const spaceAbove = y - VIEWPORT_MARGIN;
  const openAbove = spaceBelow < content && spaceAbove > spaceBelow;
  const available = Math.max(0, (openAbove ? spaceAbove : spaceBelow) - MENU_GAP);
  const maxHeight = Math.min(content, available);
  return {
    maxHeight,
    openAbove,
    left: Math.min(x, viewportW - 168),
    top: openAbove ? undefined : y,
    bottom: openAbove ? viewportH - y : undefined,
    needsScroll: content > available,
  };
}

export function FloatingAppMenu({
  items,
  anchor,
  position,
  onClose,
  placement,
  busyId = null,
}: Props) {
  const t = useMindTheme();
  const menuRef = useRef<HTMLDivElement>(null);
  const resolvedPlacement = placement ?? (isTauriDesktop() && anchor ? "panel" : "portal");
  const [layout, setLayout] = useState<MenuLayout | null>(null);

  const measureLayout = () => {
    const menu = menuRef.current;
    if (!menu) return;
    const naturalHeight = menu.scrollHeight;
    setLayout(computeMenuLayout(anchor, position, naturalHeight));
  };

  useLayoutEffect(() => {
    measureLayout();
  }, [anchor, position, items, resolvedPlacement]);

  useEffect(() => {
    const onResize = () => measureLayout();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [anchor, position, items]);

  useEffect(() => {
    const onPointerDown = (e: PointerEvent) => {
      const target = e.target as HTMLElement | null;
      if (menuRef.current?.contains(target as Node)) return;
      if (target?.closest("[data-cnexus-overlay]")) return;
      if (target?.closest("[data-cnexus-float-select-menu]")) return;
      if (target?.closest("[data-cnexus-float-menu]")) return;
      onClose();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("pointerdown", onPointerDown);
      window.removeEventListener("keydown", onKey);
    };
  }, [onClose]);

  const scrollable = layout?.needsScroll ?? false;

  const panelStyle: React.CSSProperties =
    resolvedPlacement === "panel"
      ? {
          position: "absolute",
          left: 0,
          top: layout?.openAbove ? undefined : "100%",
          bottom: layout?.openAbove ? "100%" : undefined,
          marginTop: layout?.openAbove ? undefined : MENU_GAP,
          marginBottom: layout?.openAbove ? MENU_GAP : undefined,
          minWidth: Math.max(anchor?.width ?? 168, 168),
          width: "max-content",
          height: "fit-content",
          maxHeight: layout?.maxHeight,
          overflowY: scrollable ? "auto" : "hidden",
          zIndex: 1000,
        }
      : {
          position: "fixed",
          left: layout?.left ?? anchor?.left ?? position?.x ?? 0,
          top: layout?.top,
          bottom: layout?.bottom,
          minWidth: anchor ? Math.max(anchor.width, 168) : 168,
          width: "max-content",
          height: "fit-content",
          maxHeight: layout?.maxHeight,
          overflowY: scrollable ? "auto" : "hidden",
          zIndex: 100000,
        };

  const menu = (
    <div
      ref={menuRef}
      className={`rounded-lg py-1 shadow-2xl ${floatTy.menu} w-max max-w-[min(100vw-16px,280px)] h-fit cnexus-float-scroll`}
      style={{
        ...panelStyle,
        backgroundColor: t.bg,
        border: `1px solid ${t.border}`,
        boxShadow: "0 12px 40px rgba(0,0,0,0.45)",
      }}
      data-no-drag
      role="menu"
      data-cnexus-float-menu
    >
      {items.map((item) => (
        <div key={item.id}>
          {item.separatorBefore && (
            <div className="my-1 mx-2 border-t" style={{ borderColor: t.border }} />
          )}
          <button
            type="button"
            role="menuitem"
            disabled={item.disabled || (busyId != null && busyId !== item.id)}
            className={`w-full text-left px-3 py-2.5 ${floatTy.menu} transition hover:brightness-110 whitespace-nowrap disabled:opacity-45 disabled:cursor-not-allowed inline-flex items-center gap-2`}
            style={{ color: item.danger ? t.red : t.text }}
            onPointerDown={(e) => e.stopPropagation()}
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              if (item.disabled || busyId) return;
              void Promise.resolve(item.onClick());
              onClose();
            }}
          >
            {busyId === item.id ? <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0" /> : null}
            {item.label}
          </button>
        </div>
      ))}
    </div>
  );

  if (resolvedPlacement === "panel") return menu;
  if (typeof document === "undefined") return null;
  return createPortal(menu, document.body);
}
