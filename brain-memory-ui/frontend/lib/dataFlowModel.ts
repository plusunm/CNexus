import type { CognitiveOutput, ExecLogEvent, ExecTraceManifest } from "@/lib/cognitiveTypes";
import type { MindOverview } from "@/lib/runtimeTypes";

export type FlowNodeId =
  | "input"
  | "execution"
  | "memory"
  | "cognition"
  | "governance"
  | "goal"
  | "output";

export type FlowStreamId = "chat" | "import" | "browse" | "synthesis" | "governance";

export type FlowNodeState = {
  id: FlowNodeId;
  label: string;
  sublabel: string;
  activity: number;
};

export type FlowEdgeState = {
  id: string;
  from: FlowNodeId;
  to: FlowNodeId;
  stream: FlowStreamId;
  intensity: number;
  label: string;
};

export type DataFlowModel = {
  nodes: FlowNodeState[];
  edges: FlowEdgeState[];
  highlightStream: FlowStreamId | null;
  pulses: { id: string; text: string; stream: FlowStreamId; at?: string }[];
  updatedAt?: string;
};

export const FLOW_NODE_DEFS: Omit<FlowNodeState, "activity">[] = [
  { id: "input", label: "输入", sublabel: "对话 · 上传 · 指令" },
  { id: "execution", label: "执行层", sublabel: "IR 图 · 推理 · Σ_exec" },
  { id: "memory", label: "记忆层", sublabel: "检索 · 写入 · 索引" },
  { id: "cognition", label: "认知层", sublabel: "CSE · 叙事 · 规律" },
  { id: "governance", label: "治理层", sublabel: "CDG · 稳定性 · 校正" },
  { id: "goal", label: "目标层", sublabel: "Goal Layer · 对齐" },
  { id: "output", label: "输出", sublabel: "建议 · 总结 · 行动" },
];

const EDGE_DEFS: Omit<FlowEdgeState, "intensity">[] = [
  { id: "input-execution", from: "input", to: "execution", stream: "chat", label: "对话流" },
  { id: "input-memory", from: "input", to: "memory", stream: "import", label: "导入流" },
  { id: "execution-memory", from: "execution", to: "memory", stream: "chat", label: "推理写入" },
  { id: "memory-execution", from: "memory", to: "execution", stream: "browse", label: "回忆注入" },
  { id: "memory-cognition", from: "memory", to: "cognition", stream: "synthesis", label: "合成输入" },
  { id: "execution-cognition", from: "execution", to: "cognition", stream: "synthesis", label: "轨迹压缩" },
  { id: "memory-governance", from: "memory", to: "governance", stream: "browse", label: "浏览治理" },
  { id: "cognition-governance", from: "cognition", to: "governance", stream: "governance", label: "反思校验" },
  { id: "cognition-goal", from: "cognition", to: "goal", stream: "synthesis", label: "叙事沉淀" },
  { id: "governance-goal", from: "governance", to: "goal", stream: "governance", label: "治理约束" },
  { id: "goal-output", from: "goal", to: "output", stream: "synthesis", label: "行动输出" },
];

const STREAM_LABELS: Record<FlowStreamId, string> = {
  chat: "对话流",
  import: "导入流",
  browse: "浏览流",
  synthesis: "合成流",
  governance: "治理流",
};

function clamp(n: number, min = 0, max = 1) {
  return Math.min(max, Math.max(min, n));
}

function boost(map: Record<string, number>, id: string, amount: number) {
  map[id] = clamp((map[id] ?? 0.12) + amount);
}

function nodeBoost(map: Record<FlowNodeId, number>, id: FlowNodeId, amount: number) {
  map[id] = clamp((map[id] ?? 0.08) + amount);
}

function logToFlow(log: ExecLogEvent, edges: Record<string, number>, nodes: Record<FlowNodeId, number>) {
  const cat = log.category;
  const msg = log.message.toLowerCase();

  if (cat === "ir" || cat === "chat" || cat === "execution") {
    boost(edges, "input-execution", 0.35);
    boost(edges, "execution-memory", 0.28);
    nodeBoost(nodes, "execution", 0.4);
    nodeBoost(nodes, "input", 0.2);
  }
  if (cat === "capture") {
    boost(edges, "input-memory", 0.45);
    nodeBoost(nodes, "memory", 0.45);
    nodeBoost(nodes, "input", 0.25);
  }
  if (cat === "recall") {
    boost(edges, "memory-execution", 0.38);
    nodeBoost(nodes, "memory", 0.35);
  }
  if (cat === "embed" || cat === "memory_mgmt") {
    nodeBoost(nodes, "memory", 0.3);
    boost(edges, "memory-cognition", 0.15);
  }
  if (cat === "cse") {
    boost(edges, "memory-cognition", 0.4);
    boost(edges, "execution-cognition", 0.25);
    boost(edges, "cognition-goal", 0.35);
    boost(edges, "goal-output", 0.2);
    nodeBoost(nodes, "cognition", 0.45);
    nodeBoost(nodes, "goal", 0.25);
  }
  if (cat === "governance") {
    boost(edges, "memory-governance", 0.3);
    boost(edges, "cognition-governance", 0.22);
    boost(edges, "governance-goal", 0.32);
    nodeBoost(nodes, "governance", 0.42);
  }
  if (msg.includes("502") || msg.includes("fail") || log.level === "warn" || log.level === "error") {
    boost(edges, "governance-goal", 0.15);
    nodeBoost(nodes, "governance", 0.2);
  }
}

function pulseFromLog(log: ExecLogEvent): { id: string; text: string; stream: FlowStreamId; at?: string } | null {
  const cat = log.category;
  if (cat === "ir" || cat === "chat") {
    return { id: log.id, text: "对话/执行链路激活", stream: "chat", at: log.timestamp };
  }
  if (cat === "capture") {
    return { id: log.id, text: "内容写入记忆层", stream: "import", at: log.timestamp };
  }
  if (cat === "recall") {
    return { id: log.id, text: "记忆检索注入执行", stream: "browse", at: log.timestamp };
  }
  if (cat === "cse") {
    return { id: log.id, text: "认知合成更新叙事", stream: "synthesis", at: log.timestamp };
  }
  if (cat === "governance") {
    return { id: log.id, text: "治理循环校正状态", stream: "governance", at: log.timestamp };
  }
  if (cat === "embed") {
    return { id: log.id, text: "记忆索引向量更新", stream: "import", at: log.timestamp };
  }
  return null;
}

function demoWave(phase: number): Record<string, number> {
  const streams: FlowStreamId[] = ["chat", "import", "browse", "synthesis", "governance"];
  const active = streams[Math.floor(phase) % streams.length];
  const edges: Record<string, number> = {};
  for (const e of EDGE_DEFS) {
    edges[e.id] = e.stream === active ? 0.55 + (phase % 1) * 0.25 : 0.14;
  }
  return edges;
}

export function buildDataFlowModel(input: {
  logs: ExecLogEvent[];
  traces: ExecTraceManifest[];
  data: CognitiveOutput;
  overview: MindOverview;
  isDemo: boolean;
  tick?: number;
}): DataFlowModel {
  const { logs, traces, data, overview, isDemo, tick = 0 } = input;
  const edgeIntensity: Record<string, number> = {};
  const nodeActivity: Record<FlowNodeId, number> = {
    input: 0.1,
    execution: 0.1,
    memory: 0.15,
    cognition: 0.1,
    governance: 0.1,
    goal: 0.12,
    output: 0.08,
  };

  for (const e of EDGE_DEFS) {
    edgeIntensity[e.id] = 0.12;
  }

  const recent = [...logs].slice(-24);
  for (const log of recent) {
    logToFlow(log, edgeIntensity, nodeActivity);
  }

  if (traces.length > 0) {
    boost(edgeIntensity, "input-execution", 0.2);
    boost(edgeIntensity, "execution-cognition", 0.18);
    nodeBoost(nodeActivity, "execution", 0.15);
  }

  if (data.narrative || data.summary.length) {
    boost(edgeIntensity, "cognition-goal", 0.15);
    boost(edgeIntensity, "goal-output", 0.12);
    nodeBoost(nodeActivity, "cognition", 0.12);
    nodeBoost(nodeActivity, "output", 0.1);
  }

  if (overview.system.governance_label && overview.system.governance_label !== "—") {
    nodeBoost(nodeActivity, "governance", 0.08);
  }

  const recentHasActivity = recent.some((l) => Date.now() - Date.parse(l.timestamp) < 120_000);
  if ((isDemo || !recentHasActivity) && recent.length <= 8) {
    const wave = demoWave(tick / 3);
    for (const [id, v] of Object.entries(wave)) {
      edgeIntensity[id] = Math.max(edgeIntensity[id] ?? 0, v);
    }
  }

  const edges: FlowEdgeState[] = EDGE_DEFS.map((e) => ({
    ...e,
    intensity: edgeIntensity[e.id] ?? 0.12,
  }));

  const nodes: FlowNodeState[] = FLOW_NODE_DEFS.map((n) => ({
    ...n,
    activity: nodeActivity[n.id] ?? 0.1,
  }));

  const pulses = recent
    .map(pulseFromLog)
    .filter((p): p is NonNullable<typeof p> => p != null)
    .slice(-6)
    .reverse();

  const topEdge = [...edges].sort((a, b) => b.intensity - a.intensity)[0];
  const highlightStream = topEdge && topEdge.intensity > 0.25 ? topEdge.stream : null;

  return {
    nodes,
    edges,
    highlightStream,
    pulses,
    updatedAt: logs[logs.length - 1]?.timestamp ?? data.generated_at,
  };
}

export const FLOW_STREAM_META: Record<
  FlowStreamId,
  { label: string; desc: string; themeKey: "purple" | "green" | "blue" | "orange" }
> = {
  chat: { label: STREAM_LABELS.chat, desc: "Input → Execution → Memory", themeKey: "purple" },
  import: { label: STREAM_LABELS.import, desc: "Upload → Episodic → Index", themeKey: "green" },
  browse: { label: STREAM_LABELS.browse, desc: "Memory → Recall → Context", themeKey: "blue" },
  synthesis: { label: STREAM_LABELS.synthesis, desc: "Memory → CSE → Goal → Output", themeKey: "purple" },
  governance: { label: STREAM_LABELS.governance, desc: "CDG → Stability → Goal", themeKey: "orange" },
};

/** SVG layout coordinates (viewBox 900×560) */
export const FLOW_NODE_COORDS: Record<FlowNodeId, { x: number; y: number; r: number }> = {
  input: { x: 450, y: 52, r: 34 },
  execution: { x: 175, y: 195, r: 38 },
  memory: { x: 450, y: 230, r: 46 },
  cognition: { x: 725, y: 195, r: 38 },
  governance: { x: 725, y: 370, r: 38 },
  goal: { x: 450, y: 405, r: 40 },
  output: { x: 450, y: 515, r: 32 },
};

export function edgePath(from: FlowNodeId, to: FlowNodeId): string {
  const a = FLOW_NODE_COORDS[from];
  const b = FLOW_NODE_COORDS[to];
  const mx = (a.x + b.x) / 2;
  const my = (a.y + b.y) / 2;
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const cx = mx - dy * 0.18;
  const cy = my + dx * 0.18;
  return `M ${a.x} ${a.y} Q ${cx} ${cy} ${b.x} ${b.y}`;
}
