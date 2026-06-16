import { EMPTY_MIND_OVERVIEW, type MindOverview, type RuntimeState } from "@/lib/runtimeTypes";

function placeholderHealthLabel(
  source: "runtime" | "fallback",
  bootPhase?: string | null,
): string {
  if (source === "fallback") return "离线";
  if (
    bootPhase &&
    bootPhase !== "boot_4_ready" &&
    (bootPhase.startsWith("boot_0") ||
      bootPhase.startsWith("boot_1") ||
      bootPhase.startsWith("boot_2"))
  ) {
    return "正在启动";
  }
  return "同步中";
}

/** Internal — synthesize MindOverview when Runtime payload lacks mind_overview. */
export function synthesizeOverviewFromState(
  state: RuntimeState | null,
  source: "runtime" | "fallback",
  bootPhase?: string | null,
): MindOverview {
  if (state?.mind_overview) {
    return {
      ...state.mind_overview,
      system: {
        ...state.mind_overview.system,
        api_online: source === "runtime",
      },
    };
  }

  if (!state) {
    const health_label = placeholderHealthLabel(source, bootPhase);
    return {
      ...EMPTY_MIND_OVERVIEW,
      system: {
        ...EMPTY_MIND_OVERVIEW.system,
        api_online: source === "runtime",
        health_label,
      },
    };
  }

  const beliefs = Object.values(state.beliefs ?? {});
  const topBelief = beliefs.sort((a, b) => b.confidence - a.confidence)[0];
  const sm = state.stability_metrics ?? {};
  const goalLayer = state.goal_layer as { top_goal?: Record<string, unknown> } | undefined;
  const topGoal = goalLayer?.top_goal as Record<string, unknown> | undefined;
  const workingSelf = state.working_self ?? {};
  const selfModel = state.self_model as { identity_summary?: string } | undefined;
  const narrative = state.narrative;
  const pct = (v?: number) => (v == null ? "—" : `${Math.round(v * 100)}%`);

  return {
    schema_version: "fallback",
    generated_at: state.timestamp,
    cards: {
      goal: {
        title: String(topGoal?.description ?? "暂无活跃目标"),
        progress: Number(topGoal?.progress ?? 0),
        progress_label: pct(Number(topGoal?.progress)),
        alignment: Number(topGoal?.alignment_score ?? 0),
        alignment_label: pct(Number(topGoal?.alignment_score)),
        priority: Number(topGoal?.priority ?? 0),
        priority_label: Number(topGoal?.priority ?? 0) >= 0.7 ? "高" : "中",
      },
      identity: {
        summary: selfModel?.identity_summary ?? narrative?.summary ?? "—",
        stability: sm.identity_stability ?? 0,
        stability_label: pct(sm.identity_stability),
        consistency: sm.self_consistency ?? narrative?.coherence ?? 0,
        consistency_label: pct(sm.self_consistency ?? narrative?.coherence),
        updated_ago: "—",
      },
      belief: {
        content: topBelief?.content ?? "暂无信念",
        confidence: topBelief?.confidence ?? 0,
        confidence_label: pct(topBelief?.confidence),
        evidence_count: 0,
        conflict_count: 0,
      },
      focus: {
        title: String(workingSelf.goal_focus ?? topGoal?.description ?? "—"),
        attention_label: "中",
        duration_label: "—",
        related_goals: 0,
      },
    },
    feeds: EMPTY_MIND_OVERVIEW.feeds,
    system: {
      health_score: sm.overall_stability_score ?? sm.overall_stability ?? 0,
      health_label: source === "fallback" ? "Fallback" : "同步中",
      memory_capacity_pct: Math.min(99, (state.working_memory_count ?? 0) * 5),
      governance_label: "—",
      governance_conflicts: 0,
      last_update_ago: "—",
      api_online: source === "runtime",
    },
    chat_context: {
      goal: String(topGoal?.description ?? "—").slice(0, 80),
      belief: String(topBelief?.content ?? "—").slice(0, 80),
      identity: String(selfModel?.identity_summary ?? narrative?.summary ?? "—").slice(0, 80),
    },
    memory_items: Object.entries(state.beliefs ?? {}).slice(0, 6).map(([id, b]) => ({
      id,
      title: b.content.slice(0, 120),
      tag: "belief",
      desc: `信念 · Confidence ${pct(b.confidence)}`,
      meta: `Confidence: ${pct(b.confidence)}`,
    })),
  };
}

export function resolveOverviewForSource(
  source: "demo" | "runtime" | "fallback",
  demoOverview: MindOverview,
  runtimeOverview: MindOverview | null,
  runtimeState: RuntimeState | null,
  options?: { bootPhase?: string | null },
): MindOverview {
  const bootPhase = options?.bootPhase ?? null;
  if (source === "demo") {
    if (runtimeOverview) {
      return {
        ...runtimeOverview,
        system: {
          ...runtimeOverview.system,
          api_online: false,
          health_label: runtimeOverview.system.health_label || "Demo",
        },
      };
    }
    return demoOverview;
  }
  if (runtimeOverview) {
    const label = runtimeOverview.system.health_label;
    const staleOffline = source === "runtime" && (label === "离线" || label === "—");
    return {
      ...runtimeOverview,
      system: {
        ...runtimeOverview.system,
        api_online: source === "runtime",
        health_label: staleOffline
          ? placeholderHealthLabel("runtime", bootPhase)
          : label,
      },
    };
  }
  return synthesizeOverviewFromState(
    runtimeState,
    source === "runtime" ? "runtime" : "fallback",
    bootPhase,
  );
}
