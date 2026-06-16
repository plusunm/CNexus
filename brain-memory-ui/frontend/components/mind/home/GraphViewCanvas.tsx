"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { FactorGraph } from "@/lib/factorGraphModel";
import {
  DEFAULT_GRAPH_SETTINGS,
  FLOAT_COMPACT_GRAPH_SETTINGS,
  buildGraphViewModel,
  filterGraphModel,
  type GraphViewSettings,
} from "@/lib/graphViewModel";
import { bi, biSection, floatL, homeL } from "@/lib/spine/labels";
import { useMindTheme } from "../MindUiProvider";
import type { MindTheme } from "../themes/types";
import { GraphViewControlsPanel } from "./GraphViewControlsPanel";

type Props = {
  graph: FactorGraph;
  /** Float / embedded — canvas only, no side controls */
  compact?: boolean;
  className?: string;
  layoutKey?: string;
  /** Explicit pixel frame from float layout calculator */
  frame?: { width: number; height: number };
};

const COMPACT_CANVAS_BG = "#0B0F1A";

function groupColor(theme: MindTheme, group: string): string {
  if (group === "goal" || group === "insight") return theme.green;
  if (group === "belief") return "#c9a227";
  if (group === "episode") return "#6b8cae";
  if (group === "identity") return theme.red;
  if (group === "halo") return `${theme.textMuted}55`;
  return theme.textMuted;
}

function nodeRadius(weight: number, sizeMul: number): number {
  return (4 + weight * 5.5) * sizeMul;
}

/** Obsidian 式 Graph view — 力导向球状网络 + 外环 */
export function GraphViewCanvas({ graph, compact, className, layoutKey, frame }: Props) {
  const theme = useMindTheme();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [settings, setSettings] = useState<GraphViewSettings>(
    compact ? FLOAT_COMPACT_GRAPH_SETTINGS : DEFAULT_GRAPH_SETTINGS,
  );
  const settingsRef = useRef(settings);
  settingsRef.current = settings;
  const viewRef = useRef({ scale: 1, panX: 0, panY: 0 });
  const dragRef = useRef<{ kind: "pan" | "node"; nodeId?: string; lastX: number; lastY: number } | null>(null);

  const baseModel = useMemo(() => buildGraphViewModel(graph), [graph]);
  const model = useMemo(() => filterGraphModel(baseModel, settings), [baseModel, settings]);

  const simRef = useRef<{ nodes: typeof model.nodes; links: typeof model.links }>({
    nodes: [],
    links: [],
  });

  useEffect(() => {
    simRef.current = {
      nodes: model.nodes.map((n) => ({ ...n })),
      links: model.links.map((l) => ({ ...l })),
    };
  }, [model]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let raf = 0;

    const resize = () => {
      const parentW = container.parentElement?.clientWidth ?? 0;
      let w: number;
      let h: number;
      if (compact && frame && frame.width > 0 && frame.height > 0) {
        w = Math.floor(frame.width);
        h = Math.floor(frame.height);
        container.style.width = `${w}px`;
        container.style.height = `${h}px`;
      } else {
        const measuredW = container.clientWidth;
        const measuredH = container.clientHeight;
        w = measuredW > 0 ? measuredW : Math.max(320, parentW);
        h = measuredH > 0 ? measuredH : Math.max(420, Math.round(w * 0.72));
        if (compact) {
          container.style.width = "100%";
          container.style.height = `${h}px`;
        }
      }
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(container);
    if (container.parentElement) ro.observe(container.parentElement);
    const layoutTimers = compact ? [0, 80, 220].map((ms) => window.setTimeout(resize, ms)) : [];

    const screenToWorld = (clientX: number, clientY: number) => {
      const rect = canvas.getBoundingClientRect();
      const w = container.clientWidth;
      const h = container.clientHeight;
      const { scale, panX, panY } = viewRef.current;
      const sx = clientX - rect.left;
      const sy = clientY - rect.top;
      return {
        x: (sx - w / 2 - panX) / scale,
        y: (sy - h / 2 - panY) / scale,
      };
    };

    const tick = () => {
      const w = container.clientWidth;
      const h = container.clientHeight;
      const cx = w / 2;
      const cy = h / 2;
      const { scale, panX, panY } = viewRef.current;
      const s = settingsRef.current;
      const { nodes, links } = simRef.current;
      const nodeMap = new Map(nodes.map((n) => [n.id, n]));

      if (s.animate) {
        for (const n of nodes) {
          if (n.fixed) continue;
          n.vx += (cx - (cx + n.x)) * s.centerForce * 0.002;
          n.vy += (cy - (cy + n.y)) * s.centerForce * 0.002;
        }
        for (let i = 0; i < nodes.length; i += 1) {
          for (let j = i + 1; j < nodes.length; j += 1) {
            const a = nodes[i];
            const b = nodes[j];
            const dx = b.x - a.x;
            const dy = b.y - a.y;
            const dist = Math.max(Math.hypot(dx, dy), 1);
            const force = s.repelForce / (dist * dist);
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;
            if (!a.fixed) {
              a.vx -= fx;
              a.vy -= fy;
            }
            if (!b.fixed) {
              b.vx += fx;
              b.vy += fy;
            }
          }
        }
        for (const link of links) {
          const a = nodeMap.get(link.source);
          const b = nodeMap.get(link.target);
          if (!a || !b) continue;
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const dist = Math.max(Math.hypot(dx, dy), 1);
          const delta = dist - s.linkDistance;
          const force = delta * s.linkForce * link.strength;
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          if (!a.fixed) {
            a.vx += fx;
            a.vy += fy;
          }
          if (!b.fixed) {
            b.vx -= fx;
            b.vy -= fy;
          }
        }
        for (const n of nodes) {
          if (n.fixed) continue;
          n.vx *= 0.88;
          n.vy *= 0.88;
          n.x += n.vx;
          n.y += n.vy;
        }
      }

      ctx.fillStyle = compact ? COMPACT_CANVAS_BG : theme.bg;
      ctx.fillRect(0, 0, w, h);

      const grad = ctx.createRadialGradient(cx, cy, 20, cx, cy, Math.max(w, h) * 0.55);
      grad.addColorStop(0, compact ? "#1A1F2C66" : `${theme.surface}40`);
      grad.addColorStop(1, compact ? COMPACT_CANVAS_BG : theme.bg);
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, h);

      ctx.save();
      ctx.translate(cx + panX, cy + panY);
      ctx.scale(scale, scale);

      for (const link of links) {
        const a = nodeMap.get(link.source);
        const b = nodeMap.get(link.target);
        if (!a || !b) continue;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.strokeStyle = `${theme.textMuted}44`;
        ctx.lineWidth = s.linkThickness * (0.6 + link.strength * 0.6);
        ctx.stroke();
        if (s.showArrows) {
          const ang = Math.atan2(b.y - a.y, b.x - a.x);
          const mx = (a.x + b.x) / 2;
          const my = (a.y + b.y) / 2;
          ctx.beginPath();
          ctx.moveTo(mx, my);
          ctx.lineTo(mx - Math.cos(ang - 0.4) * 6, my - Math.sin(ang - 0.4) * 6);
          ctx.lineTo(mx - Math.cos(ang + 0.4) * 6, my - Math.sin(ang + 0.4) * 6);
          ctx.closePath();
          ctx.fillStyle = `${theme.textMuted}66`;
          ctx.fill();
        }
      }

      for (const n of nodes) {
        const r = nodeRadius(n.weight, s.nodeSize);
        const color = groupColor(theme, n.group);
        ctx.beginPath();
        ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.globalAlpha = n.group === "halo" ? 0.35 : 0.92;
        ctx.fill();
        ctx.globalAlpha = 1;

        if (n.label && s.textFade > 0.05) {
          const fontBase = compact ? 8 : 9;
          ctx.font = `500 ${Math.max(7, fontBase * s.nodeSize)}px ${theme.fontSans}`;
          ctx.textAlign = "center";
          ctx.fillStyle = theme.text;
          ctx.globalAlpha = Math.min(1, s.textFade);
          const maxLen = compact ? 6 : 10;
          const short = n.label.length > maxLen ? `${n.label.slice(0, maxLen - 1)}…` : n.label;
          ctx.fillText(short, n.x, n.y + r + (compact ? 7 : 10));
          ctx.globalAlpha = 1;
        }
      }

      ctx.restore();

      if (nodes.length === 0) {
        const emptySize = compact ? 12 : 14;
        ctx.font = `500 ${emptySize}px ${theme.fontSans}`;
        ctx.textAlign = "center";
        ctx.fillStyle = theme.textMuted;
        ctx.fillText(bi(homeL.graphEmpty), cx, cy);
      }

      raf = requestAnimationFrame(tick);
    };

    const pickNode = (clientX: number, clientY: number) => {
      const { x, y } = screenToWorld(clientX, clientY);
      const s = settingsRef.current;
      const { nodes } = simRef.current;
      for (let i = nodes.length - 1; i >= 0; i -= 1) {
        const n = nodes[i];
        const r = nodeRadius(n.weight, s.nodeSize) + 4;
        if (Math.hypot(n.x - x, n.y - y) <= r) return n;
      }
      return null;
    };

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const factor = e.deltaY > 0 ? 0.92 : 1.08;
      viewRef.current.scale = Math.min(2.5, Math.max(0.35, viewRef.current.scale * factor));
    };

    const onPointerDown = (e: PointerEvent) => {
      const hit = pickNode(e.clientX, e.clientY);
      if (hit) {
        hit.fixed = true;
        dragRef.current = { kind: "node", nodeId: hit.id, lastX: e.clientX, lastY: e.clientY };
      } else {
        dragRef.current = { kind: "pan", lastX: e.clientX, lastY: e.clientY };
      }
      canvas.setPointerCapture(e.pointerId);
    };

    const onPointerMove = (e: PointerEvent) => {
      const drag = dragRef.current;
      if (!drag) return;
      const dx = e.clientX - drag.lastX;
      const dy = e.clientY - drag.lastY;
      drag.lastX = e.clientX;
      drag.lastY = e.clientY;
      if (drag.kind === "pan") {
        viewRef.current.panX += dx;
        viewRef.current.panY += dy;
        return;
      }
      const node = simRef.current.nodes.find((n) => n.id === drag.nodeId);
      if (!node) return;
      const { scale } = viewRef.current;
      node.x += dx / scale;
      node.y += dy / scale;
      node.vx = 0;
      node.vy = 0;
    };

    const onPointerUp = (e: PointerEvent) => {
      const drag = dragRef.current;
      if (drag?.kind === "node" && drag.nodeId) {
        const node = simRef.current.nodes.find((n) => n.id === drag.nodeId);
        if (node) node.fixed = false;
      }
      dragRef.current = null;
      try {
        canvas.releasePointerCapture(e.pointerId);
      } catch {
        /* ignore */
      }
    };

    canvas.addEventListener("wheel", onWheel, { passive: false });
    canvas.addEventListener("pointerdown", onPointerDown);
    canvas.addEventListener("pointermove", onPointerMove);
    canvas.addEventListener("pointerup", onPointerUp);
    canvas.addEventListener("pointercancel", onPointerUp);

    raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      for (const id of layoutTimers) window.clearTimeout(id);
      canvas.removeEventListener("wheel", onWheel);
      canvas.removeEventListener("pointerdown", onPointerDown);
      canvas.removeEventListener("pointermove", onPointerMove);
      canvas.removeEventListener("pointerup", onPointerUp);
      canvas.removeEventListener("pointercancel", onPointerUp);
    };
  }, [theme, model, compact, layoutKey, frame?.width, frame?.height]);

  if (compact) {
    const frameStyle =
      frame && frame.width > 0 && frame.height > 0
        ? { width: `${Math.floor(frame.width)}px`, height: `${Math.floor(frame.height)}px` }
        : undefined;
    return (
      <div className={className ?? "w-full"}>
        <div
          ref={containerRef}
          className="relative rounded-xl border overflow-hidden shrink-0"
          style={{
            borderColor: theme.border,
            backgroundColor: COMPACT_CANVAS_BG,
            ...frameStyle,
            ...(frameStyle ? undefined : { width: "100%", minHeight: 180 }),
          }}
        >
          <canvas
            ref={canvasRef}
            className="block w-full h-full touch-none cursor-grab active:cursor-grabbing"
            style={{ transform: "translateZ(0)" }}
            aria-label={bi(floatL.factorGraph)}
          />
        </div>
        <p className="mt-1 px-0.5 text-[10px] leading-tight truncate" style={{ color: theme.textMuted }}>
          {bi(floatL.factorGraphHint)} · {model.nodes.length}
        </p>
      </div>
    );
  }

  return (
    <div
      className="graph-view-shell grid w-full min-w-0 grid-cols-1 lg:grid-cols-[minmax(0,1fr)_var(--graph-controls-w)] rounded-xl border overflow-hidden h-auto lg:h-[var(--graph-panel-h)]"
      style={{
        borderColor: theme.border,
        ["--graph-panel-h" as string]: "min(68vh, 600px)",
        ["--graph-controls-w" as string]: "min(480px, calc(min(68vh, 600px) * 0.75))",
      }}
    >
      <div
        ref={containerRef}
        className="relative min-w-0 min-h-0 w-full h-[min(52vh,480px)] lg:h-full"
        style={{ backgroundColor: theme.bg }}
      >
        <div className="absolute top-4 left-4 z-10 pointer-events-none">
          <p className="text-lg font-semibold" style={{ color: theme.text }}>
            Graph view
          </p>
          <p className="text-xs" style={{ color: theme.textMuted }}>
            {bi(homeL.graphTitle)}
          </p>
        </div>
        <canvas ref={canvasRef} className="block w-full h-full touch-none" aria-label={bi(homeL.graphTitle)} />
      </div>
      <div
        className="min-w-0 min-h-[240px] lg:min-h-0 lg:h-full border-t lg:border-t-0 lg:border-l overflow-hidden"
        style={{ borderColor: theme.border }}
      >
        <GraphViewControlsPanel settings={settings} onChange={setSettings} graph={graph} />
      </div>
    </div>
  );
}
