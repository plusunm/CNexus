"use client";

import { useEffect, useRef } from "react";
import { FLOW_STREAM_META, type DataFlowModel, type FlowNodeId, type FlowStreamId } from "@/lib/dataFlowModel";
import type { MemoryLexeme } from "@/lib/memoryLexicon";
import { useMindTheme } from "../MindUiProvider";
import type { MindTheme } from "../themes/types";

type Props = {
  model: DataFlowModel;
  lexemes: MemoryLexeme[];
};

type Vec3 = { x: number; y: number; z: number };

const NODE_3D: Record<FlowNodeId, Vec3> = {
  input: { x: 0, y: -130, z: 60 },
  execution: { x: -200, y: -30, z: -40 },
  memory: { x: 0, y: 0, z: 0 },
  cognition: { x: 200, y: -30, z: 35 },
  governance: { x: 200, y: 90, z: -25 },
  goal: { x: 0, y: 110, z: 25 },
  output: { x: 0, y: 200, z: 55 },
};

type Particle = {
  text: string;
  stream: FlowStreamId;
  from: Vec3;
  to: Vec3;
  t: number;
  speed: number;
};

type CloudOrb = {
  lexeme: MemoryLexeme;
  theta: number;
  phi: number;
  radius: number;
};

function streamColor(theme: MindTheme, stream: FlowStreamId): string {
  const key = FLOW_STREAM_META[stream].themeKey;
  if (key === "green") return theme.green;
  if (key === "blue") return theme.blue;
  if (key === "orange") return theme.orange;
  return theme.purple;
}

function lerp3(a: Vec3, b: Vec3, u: number): Vec3 {
  return {
    x: a.x + (b.x - a.x) * u,
    y: a.y + (b.y - a.y) * u,
    z: a.z + (b.z - a.z) * u,
  };
}

function project(p: Vec3, w: number, h: number, rotY: number, fov = 620) {
  const cos = Math.cos(rotY);
  const sin = Math.sin(rotY);
  const xr = p.x * cos - p.z * sin;
  const zr = p.x * sin + p.z * cos;
  const scale = fov / (fov + zr);
  return { x: w / 2 + xr * scale, y: h / 2 + p.y * scale, scale, z: zr };
}

/** 3D 记忆词流 — 数据库词条在记忆层形成词云，并沿数据流边飞行 */
export function NeuralFlow3DCanvas({ model, lexemes }: Props) {
  const t = useMindTheme();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stateRef = useRef({
    particles: [] as Particle[],
    clouds: [] as CloudOrb[],
    rotY: 0.45,
    lexemes,
    model,
    theme: t,
  });

  stateRef.current.lexemes = lexemes;
  stateRef.current.model = model;
  stateRef.current.theme = t;

  useEffect(() => {
    stateRef.current.clouds = lexemes.slice(0, 18).map((lexeme, i) => ({
      lexeme,
      theta: (i / Math.max(lexemes.length, 1)) * Math.PI * 2,
      phi: 0.35 + (i % 5) * 0.22,
      radius: 48 + (i % 4) * 14,
    }));
  }, [lexemes]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let raf = 0;
    let last = performance.now();

    const resize = () => {
      const parent = canvas.parentElement;
      if (!parent) return;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = parent.clientWidth;
      const h = Math.max(460, Math.min(560, w * 0.58));
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    resize();
    const parent = canvas.parentElement;
    const ro = parent ? new ResizeObserver(resize) : null;
    ro?.observe(parent!);

    const spawn = () => {
      const { model: m, lexemes: words, particles } = stateRef.current;
      const hot = m.edges.filter((e) => e.intensity > 0.22);
      if (!hot.length || !words.length || particles.length > 28) return;
      const edge = hot[Math.floor(Math.random() * hot.length)];
      const pool = words.filter((w) => w.stream === edge.stream);
      const pick = (pool.length ? pool : words)[Math.floor(Math.random() * (pool.length || words.length))];
      particles.push({
        text: pick.text,
        stream: edge.stream,
        from: NODE_3D[edge.from],
        to: NODE_3D[edge.to],
        t: 0,
        speed: 0.004 + edge.intensity * 0.012,
      });
    };

    const draw = (now: number) => {
      const dt = Math.min(32, now - last);
      last = now;
      stateRef.current.rotY += dt * 0.00008;

      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      const { model: m, theme, particles, clouds, rotY } = stateRef.current;

      ctx.clearRect(0, 0, w, h);
      const bg = ctx.createRadialGradient(w / 2, h / 2, 20, w / 2, h / 2, w * 0.55);
      bg.addColorStop(0, theme.chatBg);
      bg.addColorStop(1, theme.bg);
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, w, h);

      if (Math.random() < 0.08) spawn();

      for (let i = particles.length - 1; i >= 0; i -= 1) {
        particles[i].t += particles[i].speed * (dt / 16);
        if (particles[i].t >= 1) particles.splice(i, 1);
      }

      const mem = NODE_3D.memory;
      const time = now * 0.001;
      const cloudPoints = clouds.map((c) => {
        const th = c.theta + time * 0.15;
        const ph = c.phi + Math.sin(time * 0.3 + c.theta) * 0.08;
        return {
          lexeme: c.lexeme,
          pos: {
            x: mem.x + Math.cos(th) * Math.cos(ph) * c.radius,
            y: mem.y + Math.sin(ph) * c.radius * 0.65,
            z: mem.z + Math.sin(th) * Math.cos(ph) * c.radius,
          },
        };
      });

      const nodeList = (Object.keys(NODE_3D) as FlowNodeId[]).map((id) => {
        const node = m.nodes.find((n) => n.id === id);
        return { id, pos: NODE_3D[id], activity: node?.activity ?? 0.1, label: node?.label ?? id };
      });

      type Drawable = { z: number; draw: () => void };
      const drawables: Drawable[] = [];

      for (const edge of m.edges) {
        const a = NODE_3D[edge.from];
        const b = NODE_3D[edge.to];
        const mid = lerp3(a, b, 0.5);
        mid.y -= 25;
        const pa = project(a, w, h, rotY);
        const pb = project(b, w, h, rotY);
        const pm = project(mid, w, h, rotY);
        const color = streamColor(theme, edge.stream);
        drawables.push({
          z: (pa.z + pb.z) / 2,
          draw: () => {
            ctx.beginPath();
            ctx.moveTo(pa.x, pa.y);
            ctx.quadraticCurveTo(pm.x, pm.y, pb.x, pb.y);
            ctx.strokeStyle = color;
            ctx.globalAlpha = 0.12 + edge.intensity * 0.35;
            ctx.lineWidth = 1 + edge.intensity * 2.5;
            ctx.stroke();
            ctx.globalAlpha = 1;
          },
        });
      }

      for (const c of cloudPoints) {
        const p = project(c.pos, w, h, rotY);
        const color = streamColor(theme, c.lexeme.stream);
        drawables.push({
          z: p.z,
          draw: () => {
            ctx.font = `500 ${Math.max(9, 11 * p.scale)}px ${theme.fontSans}`;
            ctx.fillStyle = color;
            ctx.globalAlpha = 0.55 + p.scale * 0.35;
            ctx.fillText(c.lexeme.text, p.x, p.y);
            ctx.globalAlpha = 1;
          },
        });
      }

      for (const p of particles) {
        const pos = lerp3(p.from, p.to, p.t);
        pos.y -= Math.sin(p.t * Math.PI) * 30;
        const pr = project(pos, w, h, rotY);
        const color = streamColor(theme, p.stream);
        drawables.push({
          z: pr.z,
          draw: () => {
            ctx.font = `600 ${Math.max(10, 12 * pr.scale)}px ${theme.fontSans}`;
            ctx.shadowColor = color;
            ctx.shadowBlur = 8;
            ctx.fillStyle = "#fff";
            ctx.globalAlpha = 0.95;
            ctx.fillText(p.text, pr.x, pr.y);
            ctx.shadowBlur = 0;
            ctx.globalAlpha = 1;
          },
        });
      }

      for (const n of nodeList) {
        const p = project(n.pos, w, h, rotY);
        const accent =
          n.id === "memory" ? "browse" : n.id === "governance" ? "governance" : n.id === "cognition" ? "synthesis" : "chat";
        drawables.push({
          z: p.z + 100,
          draw: () => {
            const r = 22 * p.scale * (1 + n.activity * 0.35);
            ctx.beginPath();
            ctx.arc(p.x, p.y, r + 8, 0, Math.PI * 2);
            ctx.fillStyle = streamColor(theme, accent as FlowStreamId);
            ctx.globalAlpha = 0.12 + n.activity * 0.2;
            ctx.fill();
            ctx.globalAlpha = 1;
            ctx.beginPath();
            ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
            ctx.strokeStyle = theme.border;
            ctx.fillStyle = theme.surface;
            ctx.lineWidth = 1.5;
            ctx.fill();
            ctx.stroke();
            ctx.font = `600 ${Math.max(10, 12 * p.scale)}px ${theme.fontSans}`;
            ctx.fillStyle = theme.text;
            ctx.textAlign = "center";
            ctx.fillText(n.label, p.x, p.y + 4);
            ctx.textAlign = "start";
          },
        });
      }

      drawables.sort((a, b) => a.z - b.z);
      for (const d of drawables) d.draw();

      ctx.font = `11px ${theme.fontSans}`;
      ctx.fillStyle = theme.textMuted;
      ctx.fillText(`记忆词条 ${lexemes.length} · 场景自动旋转`, 16, h - 14);

      raf = requestAnimationFrame(draw);
    };

    raf = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(raf);
      ro?.disconnect();
    };
  }, [lexemes]);

  return (
    <div
      className="rounded-2xl border overflow-hidden relative"
      style={{ borderColor: t.border, backgroundColor: t.chatBg }}
    >
      <canvas ref={canvasRef} className="block w-full touch-none" aria-label="3D 记忆词流演示" />
      <div
        className="flex flex-wrap gap-3 px-4 py-2 border-t text-[10px]"
        style={{ borderColor: t.border, backgroundColor: t.surface, color: t.textMuted }}
      >
        {(Object.keys(FLOW_STREAM_META) as FlowStreamId[]).map((stream) => (
          <span key={stream} className="inline-flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: streamColor(t, stream) }} />
            {FLOW_STREAM_META[stream].label}
          </span>
        ))}
        <span className="ml-auto" style={{ color: t.textLight }}>
          中心词云 = 数据库记忆 · 飞行词条 = 流动中
        </span>
      </div>
    </div>
  );
}
