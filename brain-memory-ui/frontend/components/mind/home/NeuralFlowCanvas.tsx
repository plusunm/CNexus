"use client";

import {
  edgePath,
  FLOW_NODE_COORDS,
  FLOW_NODE_DEFS,
  FLOW_STREAM_META,
  type DataFlowModel,
  type FlowNodeId,
  type FlowStreamId,
} from "@/lib/dataFlowModel";
import { useMindTheme } from "../MindUiProvider";
import type { MindTheme } from "../themes/types";

type Props = {
  model: DataFlowModel;
};

export function NeuralFlowCanvas({ model }: Props) {
  const t = useMindTheme();
  const streamColor = (stream: FlowStreamId) => {
    const key = FLOW_STREAM_META[stream].themeKey;
    if (key === "green") return t.green;
    if (key === "blue") return t.blue;
    if (key === "orange") return t.orange;
    return t.purple;
  };

  const nodeMeta = (id: FlowNodeId) =>
    model.nodes.find((n) => n.id === id) ??
    FLOW_NODE_DEFS.find((n) => n.id === id) ?? { id, label: id, sublabel: "", activity: 0.1 };

  return (
    <div
      className="rounded-2xl border overflow-hidden relative"
      style={{ borderColor: t.border, backgroundColor: t.chatBg }}
    >
      <style>{`
        @keyframes cnexus-flow-dash {
          to { stroke-dashoffset: -48; }
        }
        @keyframes cnexus-node-pulse {
          0%, 100% { opacity: 0.35; }
          50% { opacity: 0.8; }
        }
        .cnexus-flow-line {
          animation: cnexus-flow-dash linear infinite;
        }
        .cnexus-node-glow {
          animation: cnexus-node-pulse 2.4s ease-in-out infinite;
        }
      `}</style>

      <svg viewBox="0 0 900 560" className="w-full h-auto min-h-[420px]" aria-label="系统数据流神经图">
        <defs>
          {model.edges.map((edge) => {
            const c = streamColor(edge.stream);
            return (
              <linearGradient key={`g-${edge.id}`} id={`flow-grad-${edge.id}`} x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor={c} stopOpacity={0.05} />
                <stop offset="45%" stopColor={c} stopOpacity={0.35 + edge.intensity * 0.5} />
                <stop offset="100%" stopColor={c} stopOpacity={0.08} />
              </linearGradient>
            );
          })}
        </defs>

        {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => (
          <line
            key={`grid-${i}`}
            x1={0}
            y1={70 * i}
            x2={900}
            y2={70 * i}
            stroke={t.border}
            strokeOpacity={0.35}
            strokeWidth={1}
          />
        ))}

        {model.edges.map((edge) => {
          const path = edgePath(edge.from, edge.to);
          const duration = Math.max(0.8, 2.8 - edge.intensity * 2.2);
          const width = 1.5 + edge.intensity * 3.5;
          const isHot = edge.intensity > 0.35;
          return (
            <g key={edge.id}>
              <path
                d={path}
                fill="none"
                stroke={`url(#flow-grad-${edge.id})`}
                strokeWidth={width}
                strokeLinecap="round"
                opacity={0.25 + edge.intensity * 0.65}
              />
              <path
                d={path}
                fill="none"
                stroke={streamColor(edge.stream)}
                strokeWidth={Math.max(1, width - 1)}
                strokeLinecap="round"
                strokeDasharray="10 14"
                className="cnexus-flow-line"
                style={{
                  animationDuration: `${duration}s`,
                  opacity: 0.35 + edge.intensity * 0.55,
                }}
              />
              {isHot && (
                <circle r={3.5} fill={streamColor(edge.stream)} opacity={0.9}>
                  <animateMotion dur={`${duration}s`} repeatCount="indefinite" path={path} />
                </circle>
              )}
            </g>
          );
        })}

        {model.nodes.map((node) => (
          <FlowNodeGraphic key={node.id} node={node} t={t} meta={nodeMeta(node.id)} />
        ))}
      </svg>

      <StreamLegend model={model} t={t} streamColor={streamColor} />
    </div>
  );
}

function FlowNodeGraphic({
  node,
  meta,
  t,
}: {
  node: { id: FlowNodeId; activity: number };
  meta: { label: string; sublabel: string };
  t: MindTheme;
}) {
  const coord = FLOW_NODE_COORDS[node.id];
  const glow = 0.25 + node.activity * 0.55;
  const ring =
    node.id === "memory"
      ? t.blue
      : node.id === "governance"
        ? t.orange
        : node.id === "cognition"
          ? t.purple
          : node.id === "output"
            ? t.green
            : t.blue;

  return (
    <g>
      <circle
        cx={coord.x}
        cy={coord.y}
        r={coord.r + 14}
        fill={ring}
        opacity={glow * 0.22}
        className={node.activity > 0.35 ? "cnexus-node-glow" : undefined}
      />
      <circle
        cx={coord.x}
        cy={coord.y}
        r={coord.r}
        fill={t.surface}
        stroke={ring}
        strokeWidth={1.5 + node.activity * 2}
      />
      <text x={coord.x} y={coord.y - 4} textAnchor="middle" fill={t.text} fontSize={13} fontWeight={600}>
        {meta.label}
      </text>
      <text x={coord.x} y={coord.y + 12} textAnchor="middle" fill={t.textMuted} fontSize={9}>
        {meta.sublabel}
      </text>
    </g>
  );
}

function StreamLegend({
  model,
  t,
  streamColor,
}: {
  model: DataFlowModel;
  t: MindTheme;
  streamColor: (s: FlowStreamId) => string;
}) {
  const streams = Object.keys(FLOW_STREAM_META) as FlowStreamId[];
  return (
    <div
      className="flex flex-wrap gap-3 px-4 py-3 border-t"
      style={{ borderColor: t.border, backgroundColor: t.surface }}
    >
      {streams.map((stream) => {
        const active = model.highlightStream === stream;
        return (
          <div key={stream} className="flex items-center gap-2 text-[11px]">
            <span
              className="w-8 h-1 rounded-full"
              style={{
                backgroundColor: streamColor(stream),
                opacity: active ? 1 : 0.45,
                boxShadow: active ? `0 0 8px ${streamColor(stream)}` : undefined,
              }}
            />
            <span style={{ color: active ? t.text : t.textMuted }}>{FLOW_STREAM_META[stream].label}</span>
          </div>
        );
      })}
    </div>
  );
}
