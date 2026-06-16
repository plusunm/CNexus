/** Full runtime snapshot from GET /governance/state and WS /ws/state */

export type BeliefSnapshot = {
  content: string;
  confidence: number;
  evidence_count?: number;
};

export type MindOverviewCard = {
  title?: string;
  summary?: string;
  content?: string;
  progress?: number;
  progress_label?: string;
  alignment?: number;
  alignment_label?: string;
  priority?: number;
  priority_label?: string;
  stability?: number;
  stability_label?: string;
  consistency?: number;
  consistency_label?: string;
  updated_ago?: string;
  confidence?: number;
  confidence_label?: string;
  evidence_count?: number;
  conflict_count?: number;
  attention?: number;
  attention_label?: string;
  duration_label?: string;
  related_goals?: number;
};

export type MindOverviewFeedRow = { text: string; ago?: string };

export type MindOverviewMemoryItem = {
  id: string;
  title: string;
  tag: "goal" | "belief" | "episode" | "identity" | string;
  desc: string;
  meta: string;
};

export type MindOverviewDnaTrait = {
  key: string;
  label: string;
  value: number;
  value_label: string;
};

export type MindOverviewPersonality = {
  emotion: {
    primary_emotion: string;
    primary_emotion_label: string;
    intensity: number;
    intensity_label: string;
    valence: number;
    valence_label: string;
    arousal: number;
    arousal_label: string;
    dominance: number;
    dominance_label: string;
    last_updated_ago: string;
  };
  dna: {
    traits: MindOverviewDnaTrait[];
    version: string;
    mutation_count: number;
    self_consistency: number;
    self_consistency_label: string;
    overall_stability: number;
    overall_stability_label: string;
    last_updated_ago: string;
  };
  identity: MindOverviewCard;
  belief: MindOverviewCard;
};

export type MindOverviewIntentGoal = {
  goal_id: string;
  description: string;
  priority: number;
  priority_label: string;
  motivation: number;
  motivation_label: string;
  alignment_score: number;
  alignment_label: string;
  progress: number;
  progress_label: string;
  status: string;
};

export type MindOverviewIntent = {
  current_focus_id: string | null;
  current_focus_label: string;
  motivation_baseline: number;
  motivation_baseline_label: string;
  active_goal_count: number;
  goals: MindOverviewIntentGoal[];
  proactive: {
    should_trigger: boolean;
    reason: string;
    suggested_action: string;
    priority: number;
    priority_label: string;
    goal_id?: string | null;
  };
  last_updated_ago: string;
};

export type MindOverview = {
  schema_version: string;
  generated_at: string;
  goal_layer?: Record<string, unknown>;
  personality?: MindOverviewPersonality;
  intent?: MindOverviewIntent;
  cards: {
    goal: MindOverviewCard;
    identity: MindOverviewCard;
    belief: MindOverviewCard;
    focus: MindOverviewCard;
  };
  feeds: {
    episodic: MindOverviewFeedRow[];
    reflections: MindOverviewFeedRow[];
    changes: string[];
  };
  system: {
    health_score: number;
    health_label: string;
    memory_capacity_pct: number;
    governance_label: string;
    governance_conflicts?: number;
    reflective_active?: number;
    last_governance_at?: string | null;
    last_update_ago: string;
    api_online?: boolean;
  };
  chat_context: {
    goal: string;
    belief: string;
    identity: string;
  };
  memory_items: MindOverviewMemoryItem[];
};

export type RuntimeState = {
  timestamp: string;
  working_memory_count: number;
  runtime_mode?: string;
  stability_metrics: Record<string, number>;
  narrative: { summary: string; coherence: number; version: number };
  beliefs: Record<string, { content: string; confidence: number }>;
  cognitive_state?: Record<string, unknown>;
  working_self?: Record<string, unknown>;
  self_model?: Record<string, unknown>;
  reflective?: {
    active_count: number;
    pending_reviews: number;
    latest: Record<string, unknown> | null;
  };
  cdg?: Record<string, unknown>;
  metrics?: {
    counters?: Record<string, number>;
    gauges?: Record<string, number>;
    latencies?: Record<string, { count: number; p50_ms: number; p95_ms: number; max_ms: number }>;
  };
  goal_layer?: Record<string, unknown>;
  mind_overview?: MindOverview;
  last_recall_explain?: Record<string, unknown>;
};

export const EMPTY_MIND_OVERVIEW: MindOverview = {
  schema_version: "1.0.0",
  generated_at: "",
  cards: {
    goal: {
      title: "等待 Runtime 连接…",
      progress: 0,
      progress_label: "—",
      alignment: 0,
      alignment_label: "—",
      priority: 0,
      priority_label: "—",
    },
    identity: {
      summary: "等待 Runtime 连接…",
      stability: 0,
      stability_label: "—",
      consistency: 0,
      consistency_label: "—",
      updated_ago: "—",
    },
    belief: {
      content: "等待 Runtime 连接…",
      confidence: 0,
      confidence_label: "—",
      evidence_count: 0,
      conflict_count: 0,
    },
    focus: {
      title: "—",
      attention_label: "—",
      duration_label: "—",
      related_goals: 0,
    },
  },
  feeds: {
    episodic: [{ text: "暂无经历记录" }],
    reflections: [{ text: "暂无反思记录" }],
    changes: ["等待同步"],
  },
  system: {
    health_score: 0,
    health_label: "离线",
    memory_capacity_pct: 0,
    governance_label: "—",
    last_update_ago: "—",
  },
  chat_context: { goal: "—", belief: "—", identity: "—" },
  memory_items: [],
};

export const EMPTY_PERSONALITY_OBSERVATION: MindOverviewPersonality = {
  emotion: {
    primary_emotion: "neutral",
    primary_emotion_label: "平静",
    intensity: 0.5,
    intensity_label: "50%",
    valence: 0,
    valence_label: "中性",
    arousal: 0.5,
    arousal_label: "50%",
    dominance: 0.5,
    dominance_label: "50%",
    last_updated_ago: "—",
  },
  dna: {
    traits: [],
    version: "—",
    mutation_count: 0,
    self_consistency: 0,
    self_consistency_label: "—",
    overall_stability: 0,
    overall_stability_label: "—",
    last_updated_ago: "—",
  },
  identity: EMPTY_MIND_OVERVIEW.cards.identity,
  belief: EMPTY_MIND_OVERVIEW.cards.belief,
};

export const EMPTY_INTENT_OBSERVATION: MindOverviewIntent = {
  current_focus_id: null,
  current_focus_label: "—",
  motivation_baseline: 0.6,
  motivation_baseline_label: "60%",
  active_goal_count: 0,
  goals: [],
  proactive: {
    should_trigger: false,
    reason: "",
    suggested_action: "",
    priority: 0,
    priority_label: "—",
  },
  last_updated_ago: "—",
};
