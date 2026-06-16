"use client";

import { useEffect, useRef } from "react";
import type { FactorGraph, FactorNode } from "@/lib/factorGraphModel";
import { FACTOR_TAG_LABEL } from "@/lib/factorGraphModel";
import { useMindTheme } from "../MindUiProvider";
import type { MindTheme } from "../themes/types";

type Props = {
  graph: FactorGraph;
  className?: string;
  /** Float / embedded — hide legend, shorter chrome */
  compact?: boolean;
  /** Remount / resize trigger — e.g. float stage changes after Tauri window resize */
  layoutKey?: string;
};

type SimNode = {
  id: string;
  node: FactorNode;
  weightNorm: number;
  /** 归一化坐标 -1…1，布局在方形四边 */
  nx: number;
  ny: number;
  nz: number;
  pullX: number;
  pullY: number;
};

type ProjectedNode = {
  sim: SimNode;
  bx: number;
  by: number;
  x: number;
  y: number;
  z: number;
  scale: number;
  radius: number;
};

type PointerState = {
  draggingId: string | null;
  hoverId: string | null;
  mx: number;
  my: number;
};

const ROT_SPEED = 0.00055;
const BASE_FOV = 680;
const TILT_X = 0.42;
const COMPACT_MIN_SIDE = 180;
const COMPACT_MAX_SIDE = 300;
const COMPACT_FALLBACK_SIDE = 220;

/** Canvas 2d 不支持 rgba 后拼接 hex alpha；float 透明窗需不透明底色。 */
function withHexAlpha(color: string, alphaHex: string): string {
  if (color.startsWith("#") && color.length === 7) return `${color}${alphaHex}`;
  return color;
}

function canvasBackdrop(theme: MindTheme, compact?: boolean): string {
  if (compact) return "#121826";
  return theme.chatBg.startsWith("rgba") ? "#121826" : theme.chatBg;
}

function tagColor(theme: MindTheme, tag: FactorNode["tag"]): string {
  if (tag === "goal") return theme.green;
  if (tag === "belief") return theme.orange;
  if (tag === "episode") return theme.blue;
  if (tag === "identity") return theme.purple;
  if (tag === "insight") return theme.green;
  return theme.textMuted;
}

function nodeRadius(weightNorm: number, layoutScale: number): number {
  return (3.5 + weightNorm * 5.5) * layoutScale;
}

/** 沿方形四边排布：小因子贴边，大因子靠中心 */
function squareLayout(i: number, n: number, weightNorm: number): { nx: number; ny: number; nz: number } {
  if (n <= 1) return { nx: 0, ny: 0, nz: 0 };

  const t = (i + 0.5) / n;
  const perimeter = t * 4;
  const side = Math.floor(perimeter) % 4;
  const u = perimeter - Math.floor(perimeter);
  const edge = 0.06 + (1 - weightNorm) * 0.9;
  const lift = (weightNorm - 0.5) * 0.12;

  if (side === 0) return { nx: -edge + u * edge * 2, ny: lift, nz: -edge };
  if (side === 1) return { nx: edge, ny: lift, nz: -edge + u * edge * 2 };
  if (side === 2) return { nx: edge - u * edge * 2, ny: lift, nz: edge };
  return { nx: -edge, ny: lift, nz: edge - u * edge * 2 };
}

function initSimNodes(graph: FactorGraph): SimNode[] {
  if (graph.nodes.length === 0) return [];

  const weights = graph.nodes.map((n) => n.weight);
  const minW = Math.min(...weights, 1);
  const maxW = Math.max(...weights, 1);
  const span = Math.max(maxW - minW, 0.001);

  return graph.nodes.map((node, i) => {
    const weightNorm = (node.weight - minW) / span;
    const { nx, ny, nz } = squareLayout(i, graph.nodes.length, weightNorm);
    return {
      id: node.id,
      node,
      weightNorm,
      nx,
      ny,
      nz,
      pullX: 0,
      pullY: 0,
    };
  });
}

function rotateWorld(bx: number, by: number, bz: number, rotY: number): { x: number; y: number; z: number } {
  const cosT = Math.cos(TILT_X);
  const sinT = Math.sin(TILT_X);
  const ty = by * cosT - bz * sinT;
  const tz = by * sinT + bz * cosT;
  const cos = Math.cos(rotY);
  const sin = Math.sin(rotY);
  return {
    x: bx * cos - tz * sin,
    y: ty,
    z: bx * sin + tz * cos,
  };
}

function toWorld(sim: SimNode, halfSize: number, rotY: number): { x: number; y: number; z: number } {
  return rotateWorld(sim.nx * halfSize, sim.ny * halfSize, sim.nz * halfSize, rotY);
}

function project(
  p: { x: number; y: number; z: number },
  cx: number,
  cy: number,
  fov: number,
): { x: number; y: number; z: number; scale: number } {
  const scale = fov / (fov + p.z);
  return { x: cx + p.x * scale, y: cy + p.y * scale, z: p.z, scale };
}

function buildProjected(
  sims: SimNode[],
  halfSize: number,
  rotY: number,
  cx: number,
  cy: number,
  fov: number,
  layoutScale: number,
): ProjectedNode[] {
  return sims.map((sim) => {
    const world = toWorld(sim, halfSize, rotY);
    const base = project(world, cx, cy, fov);
    const radius = nodeRadius(sim.weightNorm, layoutScale) * (0.85 + base.scale * 0.2);
    return {
      sim,
      bx: base.x,
      by: base.y,
      x: base.x + sim.pullX,
      y: base.y + sim.pullY,
      z: base.z,
      scale: base.scale,
      radius,
    };
  });
}

function applyDragPulls(sims: SimNode[], graph: FactorGraph, draggedId: string) {
  const dragged = sims.find((s) => s.id === draggedId);
  if (!dragged) return;

  for (const edge of graph.edges) {
    const otherId = edge.from === draggedId ? edge.to : edge.to === draggedId ? edge.from : null;
    if (!otherId) continue;
    const other = sims.find((s) => s.id === otherId);
    if (!other) continue;
    const follow = 0.28 * edge.strength;
    other.pullX += (dragged.pullX - other.pullX) * follow;
    other.pullY += (dragged.pullY - other.pullY) * follow;
  }
}

function decayPulls(sims: SimNode[]) {
  for (const sim of sims) {
    sim.pullX *= 0.94;
    sim.pullY *= 0.94;
    if (Math.abs(sim.pullX) < 0.08) sim.pullX = 0;
    if (Math.abs(sim.pullY) < 0.08) sim.pullY = 0;
  }
}

function hitTest(projected: ProjectedNode[], mx: number, my: number): ProjectedNode | null {
  const sorted = [...projected].sort((a, b) => b.z - a.z);
  for (const p of sorted) {
    const dx = mx - p.x;
    const dy = my - p.y;
    const hitR = p.radius + 10;
    if (dx * dx + dy * dy <= hitR * hitR) return p;
  }
  return null;
}

function drawSquareFrame(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  halfSize: number,
  rotY: number,
  theme: MindTheme,
  density: number,
) {
  const corners = [
    { nx: -0.96, ny: 0, nz: -0.96 },
    { nx: 0.96, ny: 0, nz: -0.96 },
    { nx: 0.96, ny: 0, nz: 0.96 },
    { nx: -0.96, ny: 0, nz: 0.96 },
  ].map(({ nx, ny, nz }) => {
    const world = rotateWorld(nx * halfSize, ny * halfSize, nz * halfSize, rotY);
    const scale = BASE_FOV / (BASE_FOV + world.z);
    return { x: cx + world.x * scale, y: cy + world.y * scale };
  });

  ctx.save();
  ctx.beginPath();
  ctx.moveTo(corners[0].x, corners[0].y);
  for (let i = 1; i < corners.length; i += 1) ctx.lineTo(corners[i].x, corners[i].y);
  ctx.closePath();
  ctx.strokeStyle = withHexAlpha(
    theme.purple,
    Math.round(30 + density * 40)
      .toString(16)
      .padStart(2, "0"),
  );
  ctx.lineWidth = 1;
  ctx.stroke();

  const inset = halfSize * 0.06;
  ctx.beginPath();
  ctx.moveTo(corners[0].x + inset * 0.2, corners[0].y + inset * 0.2);
  for (let i = 1; i < corners.length; i += 1) ctx.lineTo(corners[i].x - inset * 0.1, corners[i].y - inset * 0.1);
  ctx.closePath();
  const grad = ctx.createRadialGradient(cx, cy, halfSize * 0.05, cx, cy, halfSize);
  grad.addColorStop(0, withHexAlpha(theme.purple, "10"));
  grad.addColorStop(0.6, withHexAlpha(theme.blue, "06"));
  grad.addColorStop(1, withHexAlpha(theme.purple, "00"));
  ctx.fillStyle = grad;
  ctx.fill();
  ctx.restore();
}

/** 因子链图 — 响应式正方 3D，因子沿方形四边分布 */
export function FactorGraphCanvas({ graph, className, compact, layoutKey }: Props) {
  const theme = useMindTheme();
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const graphRef = useRef(graph);
  const themeRef = useRef(theme);
  const simRef = useRef<SimNode[]>([]);
  const projectedRef = useRef<ProjectedNode[]>([]);
  const pointerRef = useRef<PointerState>({ draggingId: null, hoverId: null, mx: 0, my: 0 });
  const rotRef = useRef(0.4);
  const rafRef = useRef(0);
  const sizeRef = useRef(480);
  const resizeRef = useRef<(() => void) | null>(null);

  graphRef.current = graph;
  themeRef.current = theme;

  useEffect(() => {
    simRef.current = initSimNodes(graph);
    pointerRef.current.draggingId = null;
    pointerRef.current.hoverId = null;
  }, [graph]);

  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    const ctx = canvas.getContext("2d", compact ? { alpha: false } : undefined);
    if (!ctx) return;

    const measureWidth = () => {
      const rect = container.getBoundingClientRect();
      if (rect.width > 0) return rect.width;
      let el: HTMLElement | null = container.parentElement;
      for (let i = 0; i < 4 && el; i += 1) {
        const w = el.getBoundingClientRect().width;
        if (w > 0) return w;
        el = el.parentElement;
      }
      return 0;
    };

    const syncSquareSize = () => {
      if (compact) {
        const w = measureWidth() || COMPACT_FALLBACK_SIDE;
        const side = Math.max(COMPACT_MIN_SIDE, Math.min(w, COMPACT_MAX_SIDE));
        sizeRef.current = side;
        container.style.width = "100%";
        container.style.minHeight = `${side}px`;
        container.style.height = `${side}px`;
        return;
      }
      const sidebarW = 220;
      const asideW = 280;
      const gap = 12;
      const pad = 40;
      const maxW = window.innerWidth - sidebarW - asideW - gap - pad;
      const maxH = window.innerHeight - 180;
      const side = Math.max(340, Math.min(maxW, maxH));
      sizeRef.current = side;
      container.style.width = `${side}px`;
      container.style.height = `${side}px`;
    };

    const resizeCanvas = () => {
      syncSquareSize();
      const side = sizeRef.current;
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.floor(side * dpr);
      canvas.height = Math.floor(side * dpr);
      canvas.style.width = `${side}px`;
      canvas.style.height = `${side}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    resizeRef.current = resizeCanvas;
    resizeCanvas();
    const ro = new ResizeObserver(resizeCanvas);
    ro.observe(container);
    let ancestor: HTMLElement | null = container.parentElement;
    for (let i = 0; i < 3 && ancestor; i += 1) {
      ro.observe(ancestor);
      ancestor = ancestor.parentElement;
    }
    window.addEventListener("resize", resizeCanvas);
    const layoutTimers = [0, 80, 220, 480].map((ms) => window.setTimeout(resizeCanvas, ms));
    const layoutRaf = requestAnimationFrame(resizeCanvas);

    const draw = () => {
      const w = sizeRef.current;
      const h = sizeRef.current;
      if (w < 8 || h < 8) {
        rafRef.current = requestAnimationFrame(draw);
        return;
      }
      const g = graphRef.current;
      const activeTheme = themeRef.current;
      const ptr = pointerRef.current;
      const draggingId = ptr.draggingId;
      const layoutScale = compact ? w / 360 : w / 480;
      const halfSize = w * 0.4;
      const fov = BASE_FOV;

      if (!draggingId) rotRef.current += ROT_SPEED;

      const cx = w / 2;
      const cy = h / 2;

      if (draggingId) {
        const dragged = simRef.current.find((s) => s.id === draggingId);
        if (dragged) {
          const world = toWorld(dragged, halfSize, rotRef.current);
          const base = project(world, cx, cy, fov);
          dragged.pullX = ptr.mx - base.x;
          dragged.pullY = ptr.my - base.y;
        }
        applyDragPulls(simRef.current, g, draggingId);
      } else {
        decayPulls(simRef.current);
      }

      const projected = buildProjected(
        simRef.current,
        halfSize,
        rotRef.current,
        cx,
        cy,
        fov,
        layoutScale,
      );
      projectedRef.current = projected;

      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = canvasBackdrop(activeTheme, compact);
      ctx.fillRect(0, 0, w, h);

      drawSquareFrame(ctx, cx, cy, halfSize, rotRef.current, activeTheme, g.density);

      const byId = new Map(projected.map((p) => [p.sim.id, p]));
      const hoverId = ptr.hoverId;
      const edgeSorted = [...g.edges].sort((ea, eb) => {
        const za = ((byId.get(ea.from)?.z ?? 0) + (byId.get(ea.to)?.z ?? 0)) / 2;
        const zb = ((byId.get(eb.from)?.z ?? 0) + (byId.get(eb.to)?.z ?? 0)) / 2;
        return za - zb;
      });

      for (const edge of edgeSorted) {
        const a = byId.get(edge.from);
        const b = byId.get(edge.to);
        if (!a || !b) continue;
        const active =
          draggingId &&
          (edge.from === draggingId ||
            edge.to === draggingId ||
            edge.from === hoverId ||
            edge.to === hoverId);
        const depth = (a.scale + b.scale) / 2;
        const alpha = Math.round(40 + depth * 50)
          .toString(16)
          .padStart(2, "0");
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.strokeStyle = active ? activeTheme.green : withHexAlpha(activeTheme.green, alpha);
        ctx.lineWidth = 1.1 * depth * layoutScale * (active ? 1.4 : 1);
        ctx.stroke();
      }

      if (g.nodes.length === 0) {
        const emptyTitle = compact ? 14 : 13;
        const emptyHint = compact ? 12 : 11;
        ctx.font = `500 ${emptyTitle * layoutScale}px ${activeTheme.fontSans}`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillStyle = activeTheme.textMuted;
        ctx.fillText("暂无 memory 词条", cx, cy - 8);
        ctx.font = `400 ${emptyHint * layoutScale}px ${activeTheme.fontSans}`;
        ctx.fillStyle = activeTheme.textLight;
        ctx.fillText("上传或写入记忆后显示真实因子链", cx, cy + 14);
      }

      for (const p of [...projected].sort((a, b) => a.z - b.z)) {
        const color = tagColor(activeTheme, p.sim.node.tag);
        const hot = p.sim.id === draggingId || p.sim.id === hoverId;
        const r = p.radius + (hot ? 1.5 : 0);
        const alpha = 0.35 + p.scale * 0.65;

        ctx.beginPath();
        ctx.arc(p.x, p.y, r + 3, 0, Math.PI * 2);
        ctx.fillStyle = hot
          ? withHexAlpha(color, "28")
          : withHexAlpha(
              color,
              Math.round(alpha * 18)
                .toString(16)
                .padStart(2, "0"),
            );
        ctx.fill();

        ctx.beginPath();
        ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
        ctx.fillStyle = hot
          ? color
          : withHexAlpha(
              color,
              Math.round(160 + alpha * 95)
                .toString(16)
                .padStart(2, "0"),
            );
        ctx.fill();

        if (hot) {
          ctx.strokeStyle = withHexAlpha(activeTheme.text, "88");
          ctx.lineWidth = 1;
          ctx.stroke();
        }

        const fontBase = compact ? 10 : 8.5;
        const fontSize = (fontBase + p.sim.weightNorm * 3 + (hot ? 1 : 0)) * layoutScale;
        ctx.font = `${hot ? 600 : 500} ${fontSize}px ${activeTheme.fontSans}`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.fillStyle = hot
          ? activeTheme.text
          : withHexAlpha(
              activeTheme.textMuted,
              Math.round(180 + alpha * 75)
                .toString(16)
                .padStart(2, "0"),
            );
        const maxLen = compact ? 8 : layoutScale > 1.1 ? 12 : 10;
        const label =
          p.sim.node.text.length > maxLen ? `${p.sim.node.text.slice(0, maxLen - 1)}…` : p.sim.node.text;
        ctx.fillText(label, p.x, p.y + r + 4);
      }

      const hudSize = compact ? 12 : 11;
      ctx.font = `500 ${hudSize * layoutScale}px ${activeTheme.fontSans}`;
      ctx.textAlign = "left";
      ctx.fillStyle = activeTheme.textMuted;
      ctx.fillText(
        g.nodes.length > 0
          ? compact
            ? `memory ${g.nodes.length}`
            : `memory ${g.nodes.length} 条 · 沿方形四边 · 慢速旋转`
          : compact
            ? "暂无记忆词条"
            : "仅展示数据库 memory 真实词条",
        14 * layoutScale,
        18 * layoutScale,
      );
      if (!compact) {
        ctx.fillText("按住拖动，链上相邻因子缓慢跟随", 14 * layoutScale, 34 * layoutScale);
      }

      rafRef.current = requestAnimationFrame(draw);
    };

    rafRef.current = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(rafRef.current);
      cancelAnimationFrame(layoutRaf);
      for (const id of layoutTimers) window.clearTimeout(id);
      ro.disconnect();
      window.removeEventListener("resize", resizeCanvas);
      resizeRef.current = null;
    };
  }, [compact, layoutKey]);

  useEffect(() => {
    resizeRef.current?.();
    const id = window.setTimeout(() => resizeRef.current?.(), 120);
    return () => window.clearTimeout(id);
  }, [layoutKey]);

  const onPointerDown = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const hit = hitTest(projectedRef.current, mx, my);
    if (!hit) return;
    pointerRef.current.draggingId = hit.sim.id;
    pointerRef.current.hoverId = hit.sim.id;
    pointerRef.current.mx = mx;
    pointerRef.current.my = my;
    canvas.setPointerCapture(e.pointerId);
  };

  const onPointerMove = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    pointerRef.current.mx = e.clientX - rect.left;
    pointerRef.current.my = e.clientY - rect.top;
    if (pointerRef.current.draggingId) return;
    pointerRef.current.hoverId = hitTest(projectedRef.current, pointerRef.current.mx, pointerRef.current.my)?.sim.id ?? null;
  };

  const onPointerUp = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    pointerRef.current.draggingId = null;
    pointerRef.current.hoverId =
      hitTest(projectedRef.current, e.clientX - rect.left, e.clientY - rect.top)?.sim.id ?? null;
    try {
      canvas.releasePointerCapture(e.pointerId);
    } catch {
      /* ignore */
    }
  };

  const shellBg = compact ? "#1A1F2C" : theme.surface;

  return (
    <div className={`shrink-0 ${className ?? ""}`}>
      <div
        ref={containerRef}
        className={`rounded-xl border overflow-hidden ${compact ? "w-full aspect-square max-h-[300px]" : ""}`}
        style={{ borderColor: theme.border, backgroundColor: shellBg }}
      >
        <canvas
          ref={canvasRef}
          className="block w-full h-full cursor-grab active:cursor-grabbing touch-none"
          style={compact ? { transform: "translateZ(0)" } : undefined}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerLeave={onPointerUp}
        />
      </div>
      {!compact && (
      <div
        className="mt-1.5 px-1 flex flex-wrap gap-x-3 gap-y-1 text-[10px]"
        style={{ color: theme.textMuted }}
      >
        <span className="inline-flex items-center gap-1">
          <span className="w-3 h-0.5 rounded" style={{ backgroundColor: `${theme.green}66` }} />
          memory 顺序链
        </span>
        <span>小因子 · 贴方形边</span>
        <span>大因子 · 靠中心</span>
        {(Object.keys(FACTOR_TAG_LABEL) as FactorNode["tag"][]).map((tag) => (
          <span key={tag} className="inline-flex items-center gap-1">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: tagColor(theme, tag) }} />
            {FACTOR_TAG_LABEL[tag]}
          </span>
        ))}
      </div>
      )}
    </div>
  );
}
