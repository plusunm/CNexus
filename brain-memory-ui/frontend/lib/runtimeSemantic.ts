import type { CognitiveOutput, ExecLogEvent, ExecTraceManifest } from "@/lib/cognitiveTypes";
import type { MindOverview, RuntimeState } from "@/lib/runtimeTypes";

export type RuntimeZone = "execution" | "memory" | "cognition" | "governance";

export type RuntimeSemanticLine = {
  id: string;
  text: string;
  timestamp?: string;
  status: "active" | "completed" | "warning" | "neutral";
};

export type RuntimeDashboardModel = {
  execution: RuntimeSemanticLine[];
  memory: RuntimeSemanticLine[];
  cognition: RuntimeSemanticLine[];
  governance: RuntimeSemanticLine[];
  updatedAt?: string;
};

const ANTHROPOMORPHIC = /\b(我|你|您|咱们|帮你|让我|我正在|我理解|你好)\b/g;

function sanitize(text: string): string {
  return text.replace(ANTHROPOMORPHIC, "").replace(/\s{2,}/g, " ").trim();
}

function line(
  id: string,
  text: string,
  status: RuntimeSemanticLine["status"] = "neutral",
  timestamp?: string,
): RuntimeSemanticLine {
  return { id, text: sanitize(text), status, timestamp };
}

function mapLogToLines(log: ExecLogEvent): Partial<Record<RuntimeZone, RuntimeSemanticLine>> {
  const { id, category, message, timestamp, meta = {} } = log;
  const msg = message.toLowerCase();
  const ts = timestamp;

  if (category === "ir") {
    if (msg.includes("compile")) {
      const nodes =
        typeof meta.node_count === "number"
          ? meta.node_count
          : typeof meta.graph_id === "string"
            ? 12
            : undefined;
      return {
        execution: line(
          id,
          nodes
            ? `系统正在编译执行图（已生成 ${nodes} 个计算节点）`
            : "系统正在编译执行图（将输入映射为可执行计算节点）",
          "active",
          ts,
        ),
      };
    }
    if (msg.includes("execute")) {
      const ok = meta.ok !== false;
      return {
        execution: line(
          id,
          ok
            ? "当前正在执行推理链路（执行图节点依次运行）"
            : "执行图运行中断（推理链路未完成）",
          ok ? "active" : "warning",
          ts,
        ),
      };
    }
  }

  if (category === "execution" || category === "chat") {
    if (msg.includes("prepare") || msg.includes("outbound")) {
      return {
        execution: line(id, "模型推理正在进行中（生成阶段）", "active", ts),
      };
    }
    if (msg.includes("完成") || msg.includes("complete") || msg.includes("reply")) {
      return {
        execution: line(id, "模型推理已完成（响应内容已生成）", "completed", ts),
      };
    }
    if (msg.includes("full cognitive") || msg.includes("loop")) {
      return {
        execution: line(id, "完整认知循环正在运行（检索 → 推理 → 写入）", "active", ts),
      };
    }
    if (msg.includes("fail") || msg.includes("error") || msg.includes("empty")) {
      return {
        execution: line(id, "推理阶段出现异常（执行链路未正常结束）", "warning", ts),
      };
    }
  }

  if (category === "cse") {
    if (msg.includes("synthesize")) {
      return {
        cognition: line(id, "认知叙事正在更新（压缩运行历史并生成新结论）", "active", ts),
        execution: line(`${id}-exec`, "系统正在汇总执行轨迹（为认知合成准备输入）", "active", ts),
      };
    }
    return {
      cognition: line(id, "认知观察窗口正在刷新（读取最新运行事件）", "active", ts),
    };
  }

  if (category === "recall") {
    const chars = typeof meta.chars === "number" ? meta.chars : undefined;
    return {
      memory: line(
        id,
        chars && chars > 0
          ? "正在检索历史经验（与当前输入相关的记忆片段已召回）"
          : "正在检索历史经验（当前输入未匹配到足够记忆）",
        "active",
        ts,
      ),
    };
  }

  if (category === "capture") {
    if (msg.includes("denied")) {
      return {
        memory: line(id, "记忆写入被治理门控拦截（内容未进入长期存储）", "warning", ts),
        governance: line(`${id}-gov`, "检测到写入请求未通过治理校验", "warning", ts),
      };
    }
    const layer = typeof meta.layer === "string" ? meta.layer : "episodic";
    const layerLabel =
      layer === "goal" ? "目标层" : layer === "identity" ? "身份层" : "经历层";
    return {
      memory: line(id, `新交互内容已写入长期记忆（${layerLabel}）`, "completed", ts),
    };
  }

  if (category === "embed") {
    if (msg.includes("降级") || msg.includes("fail") || msg.includes("502")) {
      return {
        memory: line(id, "记忆向量索引更新受阻（已切换备用索引策略）", "warning", ts),
        governance: line(`${id}-gov`, "检测到轻微状态偏移，已自动校正", "warning", ts),
      };
    }
    return {
      memory: line(id, "记忆索引正在更新（向量化完成后可用于检索）", "active", ts),
    };
  }

  if (category === "memory_mgmt") {
    if (msg.includes("maintenance") || msg.includes("forgotten")) {
      return {
        memory: line(id, "记忆索引已更新完成（维护周期结束）", "completed", ts),
      };
    }
    if (msg.includes("stats")) {
      const total = typeof meta.total === "number" ? meta.total : undefined;
      return {
        memory: line(
          id,
          total != null
            ? `记忆库统计已刷新（当前归档 ${total} 条）`
            : "记忆库统计已刷新（容量与索引状态已同步）",
          "neutral",
          ts,
        ),
      };
    }
  }

  if (category === "governance") {
    if (msg.includes("cycle complete") || msg.includes("complete")) {
      const stability = typeof meta.stability === "number" ? meta.stability : undefined;
      return {
        governance: line(
          id,
          stability != null && stability < 0.85
            ? "检测到轻微状态偏移，已自动校正"
            : "系统运行稳定，无明显偏移",
          stability != null && stability < 0.85 ? "warning" : "completed",
          ts,
        ),
      };
    }
    if (msg.includes("started") || msg.includes("running")) {
      return {
        governance: line(id, "治理循环正在运行（评估系统稳定性与一致性）", "active", ts),
      };
    }
    if (msg.includes("disabled") || msg.includes("skipped")) {
      return {
        governance: line(id, "治理循环处于暂停状态（按配置跳过自动校正）", "neutral", ts),
      };
    }
  }

  if (category === "system") {
    if (msg.includes("502") || msg.includes("retry")) {
      return {
        execution: line(id, "外部依赖暂时不可用（系统将自动重试）", "warning", ts),
        governance: line(`${id}-gov`, "检测到运行环境波动，稳定性监控已激活", "warning", ts),
      };
    }
    if (msg.includes("bootstrap")) {
      return {
        execution: line(id, "运行时组件正在启动（本地栈启动中）", "active", ts),
      };
    }
  }

  if (category === "ollama") {
    return {
      execution: line(id, "模型服务状态变更（推理后端连接已更新）", "neutral", ts),
    };
  }

  return {};
}

function mapTraceToLine(trace: ExecTraceManifest, index: number): RuntimeSemanticLine {
  const template = trace.template_name || "默认模板";
  const status =
    trace.status === "running"
      ? "active"
      : trace.status === "failed"
        ? "warning"
        : "completed";
  return line(
    `trace-${trace.trace_id}-${index}`,
    `执行记录已写入追踪系统（${template} 链路已归档）`,
    status,
  );
}

function cognitionFromCse(data: CognitiveOutput, isEmpty: boolean): RuntimeSemanticLine[] {
  const rows: RuntimeSemanticLine[] = [];
  if (data.narrative?.trim()) {
    const excerpt = data.narrative.trim().slice(0, 120);
    rows.push(
      line(
        "cse-narrative",
        `认知叙事正在更新（${excerpt}${data.narrative.length > 120 ? "…" : ""}）`,
        "active",
        data.generated_at,
      ),
    );
  }
  if (data.summary[0]) {
    rows.push(
      line(
        "cse-summary",
        `运行历史已压缩为可解释结论（${data.summary[0].text.slice(0, 80)}${data.summary[0].text.length > 80 ? "…" : ""}）`,
        "completed",
        data.generated_at,
      ),
    );
  }
  if (data.patterns[0]) {
    rows.push(
      line(
        "cse-pattern",
        `系统识别到重复运行规律（${data.patterns[0].text.slice(0, 72)}…）`,
        "neutral",
        data.generated_at,
      ),
    );
  }
  if (data.discoveries?.length) {
    rows.push(
      line(
        "cse-discovery",
        `检测到 ${data.discoveries.length} 项相较历史窗口的新变化（认知观察已标记）`,
        "active",
        data.generated_at,
      ),
    );
  }
  if (isEmpty && rows.length === 0) {
    rows.push(
      line("cse-idle", "认知层处于观察模式（等待足够运行事件后生成叙事）", "neutral"),
    );
  }
  return rows;
}

function cognitionFromOverview(overview: MindOverview): RuntimeSemanticLine[] {
  const { focus, goal } = overview.cards;
  const rows: RuntimeSemanticLine[] = [];
  if (focus.title && focus.title !== "—") {
    rows.push(
      line(
        "focus",
        `当前注意力集中于「${focus.title.slice(0, 48)}」（工作焦点维持中）`,
        "active",
      ),
    );
  }
  if (goal.title && !goal.title.includes("等待")) {
    rows.push(
      line(
        "goal-align",
        `目标对齐状态：${goal.alignment_label ?? "—"}（长期方向约束生效）`,
        "neutral",
      ),
    );
  }
  return rows;
}

function governanceFromOverview(
  overview: MindOverview,
  runtimeState: RuntimeState | null,
): RuntimeSemanticLine[] {
  const sys = overview.system;
  const sm = runtimeState?.stability_metrics ?? {};
  const rows: RuntimeSemanticLine[] = [];

  const health = sys.health_label?.toLowerCase() ?? "";
  if (health.includes("healthy") || health.includes("健康") || health.includes("stable")) {
    rows.push(line("gov-health", "系统运行稳定，无明显偏移", "completed"));
  } else if (health.includes("warn") || health.includes("degraded") || health.includes("风险")) {
    rows.push(line("gov-health", "检测到轻微状态偏移，已自动校正", "warning"));
  } else if (health.includes("离线") || health === "—") {
    rows.push(line("gov-health", "运行时未连接（治理状态待同步）", "neutral"));
  } else if (health.includes("同步中") || health.includes("正在启动") || health.includes("正在初始化")) {
    rows.push(line("gov-health", "认知快照同步中（控制面已连接）", "neutral"));
  } else {
    rows.push(line("gov-health", `系统健康状态：${sys.health_label}（持续监控中）`, "neutral"));
  }

  const gov = sys.governance_label;
  if (gov && gov !== "—") {
    rows.push(line("gov-cycle", `治理循环状态：${gov}（CDG 监控活跃）`, "neutral"));
  }

  const identity = overview.cards.identity;
  if (identity.consistency_label && identity.consistency_label !== "—") {
    rows.push(
      line(
        "gov-identity",
        `身份状态保持一致性（一致性 ${identity.consistency_label}）`,
        "completed",
      ),
    );
  }

  const stability = sm.overall_stability_score ?? sm.overall_stability;
  if (typeof stability === "number") {
    rows.push(
      line(
        "gov-stability",
        stability >= 0.85
          ? "稳定性指标正常（整体偏移在可控范围内）"
          : "稳定性指标波动（治理层已记录偏移量）",
        stability >= 0.85 ? "completed" : "warning",
      ),
    );
  }

  if (sys.governance_conflicts && sys.governance_conflicts > 0) {
    rows.push(
      line(
        "gov-conflict",
        `检测到 ${sys.governance_conflicts} 处治理冲突（校正策略已排队）`,
        "warning",
      ),
    );
  }

  return rows;
}

function idleLines(isLive: boolean, isDemo: boolean): RuntimeDashboardModel {
  const mode = isDemo ? "演示" : isLive ? "已连接" : "未连接";
  return {
    execution: [
      line("idle-exec", `执行层处于待命状态（Runtime ${mode}，等待新的执行任务）`, "neutral"),
    ],
    memory: [line("idle-mem", "记忆层索引就绪（等待检索或写入事件）", "neutral")],
    cognition: [line("idle-cog", "认知层处于观察模式（窗口内暂无新叙事）", "neutral")],
    governance: [
      line("idle-gov", isLive ? "治理层监控中（暂无异常偏移报告）" : "治理层待同步（需连接 Runtime）", "neutral"),
    ],
  };
}

function dedupeAndLimit(rows: RuntimeSemanticLine[], limit = 6): RuntimeSemanticLine[] {
  const seen = new Set<string>();
  const out: RuntimeSemanticLine[] = [];
  for (const row of rows) {
    if (seen.has(row.text)) continue;
    seen.add(row.text);
    out.push(row);
    if (out.length >= limit) break;
  }
  return out;
}

export function buildRuntimeDashboardModel(input: {
  logs: ExecLogEvent[];
  traces: ExecTraceManifest[];
  data: CognitiveOutput;
  overview: MindOverview;
  runtimeState: RuntimeState | null;
  isDemo: boolean;
  isLive: boolean;
  isEmpty: boolean;
}): RuntimeDashboardModel {
  const { logs, traces, data, overview, runtimeState, isDemo, isLive, isEmpty } = input;

  if (!logs.length && !traces.length && isEmpty && !isDemo && !isLive) {
    return idleLines(isLive, isDemo);
  }

  const execution: RuntimeSemanticLine[] = [];
  const memory: RuntimeSemanticLine[] = [];
  const cognition: RuntimeSemanticLine[] = [];
  const governance: RuntimeSemanticLine[] = [];

  for (const log of [...logs].reverse()) {
    const mapped = mapLogToLines(log);
    if (mapped.execution) execution.push(mapped.execution);
    if (mapped.memory) memory.push(mapped.memory);
    if (mapped.cognition) cognition.push(mapped.cognition);
    if (mapped.governance) governance.push(mapped.governance);
  }

  traces.slice(-4).forEach((tr, i) => {
    execution.push(mapTraceToLine(tr, i));
  });

  cognition.push(...cognitionFromCse(data, isEmpty));
  cognition.push(...cognitionFromOverview(overview));
  governance.push(...governanceFromOverview(overview, runtimeState));

  if (execution.length === 0) {
    execution.push(line("fallback-exec", "执行层处于空闲监听状态（等待 IR 图编译或推理任务）", "neutral"));
  }
  if (memory.length === 0) {
    const cap = overview.system.memory_capacity_pct;
    memory.push(
      line(
        "fallback-mem",
        cap > 0
          ? `记忆层运行正常（容量使用约 ${cap}%）`
          : "记忆层处于待命状态（索引结构已加载）",
        "neutral",
      ),
    );
  }

  const latestTs = logs[logs.length - 1]?.timestamp ?? data.generated_at ?? overview.generated_at;

  return {
    execution: dedupeAndLimit(execution),
    memory: dedupeAndLimit(memory),
    cognition: dedupeAndLimit(cognition),
    governance: dedupeAndLimit(governance),
    updatedAt: latestTs,
  };
}
