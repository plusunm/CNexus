"use client";

import { useEffect, useMemo, useRef } from "react";
import { eventTypeLabel } from "@/lib/spineMapper";
import type { SpineEvent } from "@/lib/spineTypes";
import { useSpineStore } from "@/lib/spineStore";
import { bi, biSection, debuggerL } from "@/lib/spine/labels";
import { useMindTheme } from "../MindUiProvider";
import type { MindTheme } from "../themes/types";

type Props = { events: SpineEvent[] };

type SimNode = {
  id: string;
  label: string;
  group: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  weight: number;
};

function groupColor(theme: MindTheme, group: string, decision?: string): string {
  if (decision === "REJECT") return theme.red;
  if (decision === "WARN") return theme.orange;
  if (group === "capture" || group === "commit") return theme.green;
  if (group === "cdg") return "#c9a227";
  if (group === "recall") return "#6b8cae";
  if (group === "control") return theme.red;
  return theme.purple;
}

/** Obsidian 式因果图 — Spine 的 causal 投影 */
export function SpineCausalGraph({ events }: Props) {
  const theme = useMindTheme();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const selectedEventId = useSpineStore((s) => s.selectedEventId);
  const selectEvent = useSpineStore((s) => s.selectEvent);

  const model = useMemo(() => {
    const nodes: SimNode[] = events.map((e, i) => {
      const angle = (i / Math.max(events.length, 1)) * Math.PI * 2;
      const r = 80 + (i % 4) * 40;
      return {
        id: e.event_id,
        label: eventTypeLabel(e.event_type),
        group: e.event_type,
        x: Math.cos(angle) * r,
        y: Math.sin(angle) * r,
        vx: 0,
        vy: 0,
        weight: e.action === "commit" ? 1.4 : 1,
      };
    });
    const links: { source: string; target: string }[] = [];
    for (const e of events) {
      if (e.parent_event_id) links.push({ source: e.parent_event_id, target: e.event_id });
      for (const c of e.causal_links ?? []) {
        if (c !== e.parent_event_id) links.push({ source: c, target: e.event_id });
      }
    }
    return { nodes, links };
  }, [events]);

  const simRef = useRef(model);
  simRef.current = {
    nodes: model.nodes.map((n) => ({ ...n })),
    links: model.links.map((l) => ({ ...l })),
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let raf = 0;
    const resize = () => {
      const w = container.clientWidth;
      const h = container.clientHeight;
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

    const tick = () => {
      const w = container.clientWidth;
      const h = container.clientHeight;
      const cx = w / 2;
      const cy = h / 2;
      const { nodes, links } = simRef.current;
      const nodeMap = new Map(nodes.map((n) => [n.id, n]));

      for (const n of nodes) {
        n.vx += (cx - (cx + n.x)) * 0.0004;
        n.vy += (cy - (cy + n.y)) * 0.0004;
      }
      for (let i = 0; i < nodes.length; i += 1) {
        for (let j = i + 1; j < nodes.length; j += 1) {
          const a = nodes[i];
          const b = nodes[j];
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const dist = Math.max(Math.hypot(dx, dy), 1);
          const f = 90 / (dist * dist);
          a.vx -= (dx / dist) * f;
          a.vy -= (dy / dist) * f;
          b.vx += (dx / dist) * f;
          b.vy += (dy / dist) * f;
        }
      }
      for (const link of links) {
        const a = nodeMap.get(link.source);
        const b = nodeMap.get(link.target);
        if (!a || !b) continue;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dist = Math.max(Math.hypot(dx, dy), 1);
        const f = (dist - 72) * 0.03;
        a.vx += (dx / dist) * f;
        a.vy += (dy / dist) * f;
        b.vx -= (dx / dist) * f;
        b.vy -= (dy / dist) * f;
      }
      for (const n of nodes) {
        n.vx *= 0.88;
        n.vy *= 0.88;
        n.x += n.vx;
        n.y += n.vy;
      }

      ctx.fillStyle = theme.bg;
      ctx.fillRect(0, 0, w, h);
      const grad = ctx.createRadialGradient(cx, cy, 20, cx, cy, Math.max(w, h) * 0.5);
      grad.addColorStop(0, `${theme.surface}50`);
      grad.addColorStop(1, theme.bg);
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, h);

      for (const link of links) {
        const a = nodeMap.get(link.source);
        const b = nodeMap.get(link.target);
        if (!a || !b) continue;
        ctx.beginPath();
        ctx.moveTo(cx + a.x, cy + a.y);
        ctx.lineTo(cx + b.x, cy + b.y);
        ctx.strokeStyle = `${theme.textMuted}44`;
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      for (const n of nodes) {
        const ev = events.find((e) => e.event_id === n.id);
        const r = (5 + n.weight * 4) * (selectedEventId === n.id ? 1.3 : 1);
        const color = groupColor(theme, n.group, ev?.decision?.decision);
        ctx.beginPath();
        ctx.arc(cx + n.x, cy + n.y, r, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.globalAlpha = selectedEventId && selectedEventId !== n.id ? 0.45 : 0.92;
        ctx.fill();
        ctx.globalAlpha = 1;
        ctx.font = `500 8px ${theme.fontSans}`;
        ctx.textAlign = "center";
        ctx.fillStyle = theme.text;
        ctx.fillText(n.label, cx + n.x, cy + n.y + r + 9);
      }

      if (nodes.length === 0) {
        ctx.font = `500 13px ${theme.fontSans}`;
        ctx.textAlign = "center";
        ctx.fillStyle = theme.textMuted;
        ctx.fillText(debuggerL.waitForTrace.zh, cx, cy);
      }

      raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, [theme, events, selectedEventId]);

  const onClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;
    const rect = canvas.getBoundingClientRect();
    const sx = e.clientX - rect.left;
    const sy = e.clientY - rect.top;
    const cx = container.clientWidth / 2;
    const cy = container.clientHeight / 2;
    const { nodes } = simRef.current;
    for (let i = nodes.length - 1; i >= 0; i -= 1) {
      const n = nodes[i];
      if (Math.hypot(sx - (cx + n.x), sy - (cy + n.y)) <= 12) {
        selectEvent(n.id);
        return;
      }
    }
  };

  return (
    <div ref={containerRef} className="flex-1 min-h-[420px] relative" style={{ backgroundColor: theme.bg }}>
      <div className="absolute top-3 left-4 z-10 pointer-events-none">
        <p className="text-sm font-semibold" style={{ color: theme.text }}>
          Causal Graph
        </p>
        <p className="text-[10px]" style={{ color: theme.textMuted }}>
          {bi(debuggerL.causalProjection)}
        </p>
      </div>
      <canvas ref={canvasRef} className="w-full h-full min-h-[420px] touch-none cursor-pointer" onClick={onClick} />
    </div>
  );
}
