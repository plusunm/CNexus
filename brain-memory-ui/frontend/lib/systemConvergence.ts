/**
 * CNEXUS System Convergence — single source for Boot v3 + 3-domain + L3 + Kernel.
 * Used by docs, React Flow / neural flow UI, and connection diagnostics.
 *
 * @see docs/CNEXUS_SYSTEM_CONVERGENCE.md
 */

/** API `boot_phase` strings — must match `core/runtime/boot_protocol.py` BootPhase */
export type BootPhaseId =
  | "boot_0_api"
  | "boot_1_runtime_spawned"
  | "boot_2_hydrating"
  | "boot_3_cognitive_warming"
  | "boot_4_ready";

export type SystemDomainId = "control" | "runtime" | "storage" | "cognitive";

export type BootPhaseMeta = {
  id: BootPhaseId;
  /** Docs / UI label (BOOT_0_API_READY style) */
  label: string;
  order: number;
  allowsIo: boolean;
  allowsCognition: boolean;
  description: { en: string; zh: string };
};

export const BOOT_PROTOCOL_VERSION = "boot-protocol-v3";

export const BOOT_PHASES: BootPhaseMeta[] = [
  {
    id: "boot_0_api",
    label: "BOOT_0_API",
    order: 0,
    allowsIo: false,
    allowsCognition: false,
    description: {
      en: "API listening — control plane alive",
      zh: "API 已监听 — 控制面存活",
    },
  },
  {
    id: "boot_1_runtime_spawned",
    label: "BOOT_1_RUNTIME",
    order: 1,
    allowsIo: false,
    allowsCognition: false,
    description: {
      en: "Runtime spawned on worker thread",
      zh: "Runtime 已在工作线程 spawn",
    },
  },
  {
    id: "boot_2_hydrating",
    label: "BOOT_2_HYDRATE",
    order: 2,
    allowsIo: true,
    allowsCognition: false,
    description: {
      en: "Storage hydrate (worker only)",
      zh: "存储 hydrate 中（仅 worker）",
    },
  },
  {
    id: "boot_3_cognitive_warming",
    label: "BOOT_3_COGNITIVE",
    order: 3,
    allowsIo: true,
    allowsCognition: true,
    description: {
      en: "Cognitive warmup — throttled governance",
      zh: "认知模块正在启动",
    },
  },
  {
    id: "boot_4_ready",
    label: "BOOT_4_READY",
    order: 4,
    allowsIo: true,
    allowsCognition: true,
    description: {
      en: "Stable ready — full system operational",
      zh: "稳定就绪 — 全系统可操作",
    },
  },
];

/** Legacy v2 API strings → v3 */
export const LEGACY_BOOT_PHASE_MAP: Record<string, BootPhaseId> = {
  boot_1_state: "boot_1_runtime_spawned",
  boot_2_hydrate: "boot_2_hydrating",
  boot_2_cognitive: "boot_3_cognitive_warming",
  boot_3_optimized: "boot_4_ready",
};

export function normalizeBootPhase(raw: string | null | undefined): BootPhaseId | null {
  if (!raw) return null;
  if (BOOT_PHASES.some((p) => p.id === raw)) return raw as BootPhaseId;
  return LEGACY_BOOT_PHASE_MAP[raw] ?? null;
}

export function bootPhaseMeta(phase: BootPhaseId | null): BootPhaseMeta | null {
  if (!phase) return null;
  return BOOT_PHASES.find((p) => p.id === phase) ?? null;
}

export function bootPhaseOrder(phase: BootPhaseId | null): number {
  return bootPhaseMeta(phase)?.order ?? -1;
}

/** Unified ready display — mirrors evaluate_system_ready() semantics for UI */
export type ReadyDisplay = "ready" | "warming" | "offline" | "not_ready";

export function resolveReadyDisplay(payload: {
  status?: string;
  boot_phase?: string;
  ws?: string;
  render_mode?: string;
} | null): ReadyDisplay {
  if (!payload) return "offline";
  if (payload.status === "ready_fast" || payload.render_mode === "fast_path_v1") {
    return "warming";
  }
  if (payload.status === "streaming" || payload.render_mode === "fast_path_v2") {
    return "warming";
  }
  if (payload.render_mode === "fast_path_v3" || (payload as { mode?: string }).mode === "fast-path-v3") {
    return "warming";
  }
  if (payload.status === "ready" && payload.boot_phase === "boot_4_ready" && payload.ws === "alive") {
    return "ready";
  }
  if (payload.status === "warming") return "warming";
  if (payload.status === "not_ready") return "not_ready";
  return "offline";
}

/** React Flow / canvas node graph — boot state machine */
export type ConvergenceGraphNode = {
  id: string;
  label: string;
  domain: SystemDomainId | "boot";
  x: number;
  y: number;
};

export type ConvergenceGraphEdge = {
  id: string;
  from: string;
  to: string;
  label?: string;
};

export const BOOT_PHASE_GRAPH: {
  nodes: ConvergenceGraphNode[];
  edges: ConvergenceGraphEdge[];
} = {
  nodes: BOOT_PHASES.map((p, i) => ({
    id: p.id,
    label: p.label,
    domain: "boot" as const,
    x: 80 + i * 160,
    y: 120,
  })),
  edges: BOOT_PHASES.slice(0, -1).map((p, i) => ({
    id: `${p.id}->${BOOT_PHASES[i + 1].id}`,
    from: p.id,
    to: BOOT_PHASES[i + 1].id,
  })),
};

/** Three-domain architecture graph */
export const THREE_DOMAIN_GRAPH: {
  nodes: ConvergenceGraphNode[];
  edges: ConvergenceGraphEdge[];
} = {
  nodes: [
    { id: "control", label: "CONTROL PLANE", domain: "control", x: 400, y: 40 },
    { id: "runtime", label: "RUNTIME", domain: "runtime", x: 400, y: 160 },
    { id: "storage", label: "STORAGE", domain: "storage", x: 200, y: 280 },
    { id: "cognitive", label: "COGNITIVE", domain: "cognitive", x: 600, y: 280 },
  ],
  edges: [
    { id: "control->runtime", from: "control", to: "runtime", label: "peek pointer" },
    { id: "runtime->storage", from: "runtime", to: "storage", label: "hydrate" },
    { id: "runtime->cognitive", from: "runtime", to: "cognitive", label: "warmup" },
  ],
};

/** L3 scheduler spec — UI / docs mirror of Python prototype */
export const L3_SCHEDULER_SPEC = {
  version: "l3-scheduler-v0",
  defaultSliceMs: 30,
  maxSliceMs: 50,
  taskTypes: ["cdg_cpu", "memory_reflect", "llm_deferred", "storage_batch"] as const,
};

export type L3SchedulerStatus = {
  scheduler?: string;
  ticks?: number;
  queue_length?: number;
  slice_ms?: number;
  last_tick?: {
    tick_cost_ms?: number;
    remaining?: number;
    last_executed?: string[];
  } | null;
};

export function parseL3Status(boot: Record<string, unknown> | null | undefined): L3SchedulerStatus | null {
  if (!boot || typeof boot !== "object") return null;
  const l3 = boot.l3;
  if (!l3 || typeof l3 !== "object") return null;
  return l3 as L3SchedulerStatus;
}

/** Kernel survival contract — documentation constants */
export const KERNEL_CONTRACT = {
  version: "control-plane-kernel-v0",
  maxReadyResponseMs: 200,
  guarantees: ["no_init_on_request", "no_io_on_loop", "no_cognitive_import_on_ready"] as const,
};

/** Map boot phase to neural-flow node emphasis (for NeuralFlow3DCanvas overlays) */
export const BOOT_TO_FLOW_NODE: Partial<
  Record<BootPhaseId, "execution" | "memory" | "cognition" | "governance">
> = {
  boot_1_runtime_spawned: "execution",
  boot_2_hydrating: "memory",
  boot_3_cognitive_warming: "cognition",
  boot_4_ready: "governance",
};
