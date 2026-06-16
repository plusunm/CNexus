"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ChevronDown } from "lucide-react";
import { floatTy } from "@/lib/floatTypography";
import { useMindTheme } from "../MindUiProvider";

export type FloatSelectOption = { value: string; label: string };

type Props = {
  value: string;
  options: FloatSelectOption[];
  onChange: (value: string) => void;
  label?: string;
  /** Render dropdown in document body — avoids WebView2 / overflow clipping */
  menuPortal?: boolean;
};

/** Custom dropdown for Tauri float windows (native <select> popups clip on frameless WebView2). */
export function FloatSelect({ value, options, onChange, label, menuPortal = false }: Props) {
  const t = useMindTheme();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const [menuRect, setMenuRect] = useState<{ left: number; top: number; width: number } | null>(
    null,
  );

  const measureMenu = () => {
    const trigger = triggerRef.current;
    if (!trigger) return;
    const rect = trigger.getBoundingClientRect();
    setMenuRect({
      left: rect.left,
      top: rect.bottom + 4,
      width: Math.max(rect.width, 168),
    });
  };

  useLayoutEffect(() => {
    if (!open || !menuPortal) return;
    measureMenu();
  }, [open, menuPortal, value, options.length]);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: PointerEvent) => {
      const target = e.target as Node | null;
      if (rootRef.current?.contains(target)) return;
      if (menuPortal && (target as HTMLElement | null)?.closest("[data-cnexus-float-select-menu]")) {
        return;
      }
      setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    const onResize = () => {
      if (menuPortal) measureMenu();
    };
    window.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("keydown", onKey);
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("pointerdown", onPointerDown);
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", onResize);
    };
  }, [open, menuPortal]);

  const selected = options.find((o) => o.value === value)?.label ?? value;

  const menu = open ? (
    <div
      role="listbox"
      data-cnexus-float-select-menu
      className="rounded-lg py-1 shadow-2xl max-h-44 overflow-y-auto cnexus-float-scroll"
      style={
        menuPortal && menuRect
          ? {
              position: "fixed",
              left: menuRect.left,
              top: menuRect.top,
              minWidth: menuRect.width,
              zIndex: 2147483647,
              backgroundColor: t.bg,
              border: `1px solid ${t.border}`,
              boxShadow: "0 8px 24px rgba(0,0,0,0.45)",
            }
          : {
              position: "absolute",
              left: 0,
              right: 0,
              top: "100%",
              marginTop: 4,
              zIndex: 1000,
              backgroundColor: t.bg,
              border: `1px solid ${t.border}`,
              boxShadow: "0 8px 24px rgba(0,0,0,0.45)",
            }
      }
    >
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          role="option"
          aria-selected={opt.value === value}
          className={`w-full text-left px-2.5 py-2 ${floatTy.body} hover:brightness-110`}
          style={{
            color: opt.value === value ? t.green : t.text,
            backgroundColor: opt.value === value ? `${t.green}22` : undefined,
          }}
          onClick={() => {
            onChange(opt.value);
            setOpen(false);
          }}
        >
          {opt.label}
        </button>
      ))}
    </div>
  ) : null;

  return (
    <div className="flex flex-col gap-1 relative" ref={rootRef} data-no-drag>
      {label && (
        <span className={floatTy.caption} style={{ color: t.textMuted }}>
          {label}
        </span>
      )}
      <button
        ref={triggerRef}
        type="button"
        className={`flex items-center justify-between gap-2 border rounded-lg px-2.5 py-2 ${floatTy.input} w-full text-left`}
        style={{ borderColor: t.border, backgroundColor: t.surface, color: t.text }}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="listbox"
      >
        <span className="truncate">{selected}</span>
        <ChevronDown className="w-3.5 h-3.5 shrink-0" style={{ color: t.textMuted }} />
      </button>
      {menuPortal && typeof document !== "undefined" && menu
        ? createPortal(menu, document.body)
        : menu}
    </div>
  );
}
