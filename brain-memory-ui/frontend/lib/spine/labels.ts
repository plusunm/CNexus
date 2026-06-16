/** Execution Spine UI — bilingual labels (EN / 中文). */

import type { LanguageProjectionMode } from "@/lib/sibt/projectionMode";

export type BilingualLabel = { en: string; zh: string };

/** Project label to single language or bilingual per SIBT UI mode. */
export function projectLabel(label: BilingualLabel, mode: LanguageProjectionMode = "both"): string {
  if (mode === "en") return label.en;
  if (mode === "zh") return label.zh;
  return `${label.en} / ${label.zh}`;
}

/** Section heading with projection mode. */
export function projectBiSection(label: BilingualLabel, mode: LanguageProjectionMode = "both"): string {
  if (mode === "en") return label.en;
  if (mode === "zh") return label.zh;
  return `${label.en} · ${label.zh}`;
}

/** Render as "English / 中文" */
export function bi(label: BilingualLabel): string {
  return `${label.en} / ${label.zh}`;
}

/** Section heading: English · 中文 */
export function biSection(label: BilingualLabel): string {
  return `${label.en} · ${label.zh}`;
}

/** Bilingual template: replace {key} in both en and zh */
export function biFmt(label: BilingualLabel, vars: Record<string, string | number>): string {
  let en = label.en;
  let zh = label.zh;
  for (const [key, val] of Object.entries(vars)) {
    const token = `{${key}}`;
    en = en.split(token).join(String(val));
    zh = zh.split(token).join(String(val));
  }
  return `${en} / ${zh}`;
}

export const spineL = {
  appTitle: { en: "Execution Spine", zh: "执行观测" } satisfies BilingualLabel,
  eivTitle: { en: "Execution Identity Viewer", zh: "执行标识视图" } satisfies BilingualLabel,
  eivSubtitle: {
    en: "Identity class · trace instance · causal structure · state diff",
    zh: "执行标识 · 追踪实例 · 因果链 · 状态变更",
  } satisfies BilingualLabel,
  appSubtitle: {
    en: "One trace · trigger → causal → state → control → explain",
    zh: "单次追踪 · 触发 → 因果 → 状态 → 管控 → 解释",
  } satisfies BilingualLabel,

  trace: { en: "TRACE", zh: "追踪" } satisfies BilingualLabel,
  status: { en: "STATUS", zh: "状态" } satisfies BilingualLabel,
  source: { en: "SOURCE", zh: "来源" } satisfies BilingualLabel,
  mode: { en: "MODE", zh: "模式" } satisfies BilingualLabel,
  events: { en: "events", zh: "事件" } satisfies BilingualLabel,
  semantic: { en: "semantic", zh: "语义关联" } satisfies BilingualLabel,

  statusLive: { en: "LIVE", zh: "实时" } satisfies BilingualLabel,
  statusReplay: { en: "REPLAY", zh: "回放" } satisfies BilingualLabel,
  statusOffline: { en: "OFFLINE", zh: "离线" } satisfies BilingualLabel,
  statusStale: { en: "STALE", zh: "已过期" } satisfies BilingualLabel,

  query: { en: "QUERY", zh: "查询" } satisfies BilingualLabel,
  queryPlaceholder: {
    en: "TRACE <id> EXPLAIN causal",
    zh: "TRACE <id> EXPLAIN causal",
  } satisfies BilingualLabel,
  runtimeRequired: {
    en: "Runtime not connected — spine_events.jsonl required",
    zh: "未连接运行时，需可读的 spine_events.jsonl",
  } satisfies BilingualLabel,

  streamLive: { en: "STREAM LIVE", zh: "执行流已订阅" } satisfies BilingualLabel,
  streamConnecting: { en: "SUBSCRIBING…", zh: "正在订阅执行流…" } satisfies BilingualLabel,
  stream: { en: "STREAM", zh: "推送" } satisfies BilingualLabel,
  streamOff: { en: "STREAM OFF", zh: "推送关闭" } satisfies BilingualLabel,
  liveSpineStream: { en: "Live Spine Stream", zh: "实时解释流" } satisfies BilingualLabel,
  waitingFrames: {
    en: "Waiting for explanation frames…",
    zh: "等待解释更新…",
  } satisfies BilingualLabel,
  openLiveStream: { en: "Open live stream", zh: "打开实时流" } satisfies BilingualLabel,
  frameCount: { en: "frames", zh: "条更新" } satisfies BilingualLabel,

  loading: { en: "Loading execution spine…", zh: "正在加载执行数据…" } satisfies BilingualLabel,
  liveStreamError: { en: "Live stream", zh: "实时流异常" } satisfies BilingualLabel,
  emptyPrompt: {
    en: "Enter TRACE <id> and QUERY to load an execution record.",
    zh: "输入 TRACE <id> 与查询语句以加载执行记录",
  } satisfies BilingualLabel,
  queryFailed: { en: "Query failed", zh: "查询失败" } satisfies BilingualLabel,

  timeline: { en: "Execution Spine Timeline", zh: "执行时序" } satisfies BilingualLabel,
  noExecutionEvents: {
    en: "No execution events in this trace.",
    zh: "该追踪暂无执行事件",
  } satisfies BilingualLabel,
  stateDelta: { en: "Δ state", zh: "状态变化" } satisfies BilingualLabel,
  triggeredBy: { en: "triggered_by from", zh: "触发来源" } satisfies BilingualLabel,

  causalLens: { en: "Causal Lens", zh: "因果分析" } satisfies BilingualLabel,
  noCausal: { en: "No causal chain from backend.", zh: "暂无因果链数据" } satisfies BilingualLabel,
  rootCause: { en: "Root cause", zh: "根因" } satisfies BilingualLabel,

  stateEvolution: { en: "State Evolution", zh: "状态演变" } satisfies BilingualLabel,
  noStateTrajectory: {
    en: "No state trajectory in contract.",
    zh: "暂无状态变更记录",
  } satisfies BilingualLabel,

  controlDecision: { en: "Control & Decision", zh: "管控决策" } satisfies BilingualLabel,
  noControl: {
    en: "No control decisions in this trace.",
    zh: "该追踪暂无管控记录",
  } satisfies BilingualLabel,
  entry: { en: "entry", zh: "入口" } satisfies BilingualLabel,
  caller: { en: "caller", zh: "调用方" } satisfies BilingualLabel,

  explanation: { en: "Explanation", zh: "解释" } satisfies BilingualLabel,
  noExplanation: {
    en: "No explanation from backend for this trace.",
    zh: "该追踪暂无解释内容",
  } satisfies BilingualLabel,
  path: { en: "path", zh: "路径" } satisfies BilingualLabel,

  executionMode: { en: "execution_spine_v1", zh: "execution_spine_v1" } satisfies BilingualLabel,
  executionSource: { en: "execution_spine", zh: "execution_spine" } satisfies BilingualLabel,

  driftPanel: { en: "Runtime ↔ Spine Drift", zh: "运行时与日志偏差" } satisfies BilingualLabel,
  driftScore: { en: "DRIFT SCORE", zh: "偏差指数" } satisfies BilingualLabel,
  driftMissing: { en: "Missing", zh: "缺失" } satisfies BilingualLabel,
  driftExtra: { en: "Extra", zh: "冗余" } satisfies BilingualLabel,
  driftMismatch: { en: "Mismatch", zh: "不匹配" } satisfies BilingualLabel,
  driftSync: { en: "Spine sync", zh: "日志同步" } satisfies BilingualLabel,
  driftConfidence: { en: "confidence", zh: "置信度" } satisfies BilingualLabel,
  driftStatusOk: { en: "OK", zh: "一致" } satisfies BilingualLabel,
  driftStatusMissing: { en: "MISSING", zh: "缺失" } satisfies BilingualLabel,
  driftStatusExtra: { en: "EXTRA", zh: "冗余" } satisfies BilingualLabel,
  driftStatusSuspect: { en: "SUSPECT", zh: "存疑" } satisfies BilingualLabel,
  noDriftData: {
    en: "No drift report — query with engine v2 in Runtime mode",
    zh: "暂无偏差报告，请在运行时模式下使用 v2 引擎查询",
  } satisfies BilingualLabel,

  epistemicScore: { en: "Epistemic confidence", zh: "解释可信度" } satisfies BilingualLabel,
  explainCaveats: { en: "Drift caveats", zh: "偏差说明" } satisfies BilingualLabel,

  identityPanel: { en: "Execution Identity", zh: "执行标识" } satisfies BilingualLabel,
  identityHash: { en: "IDENTITY", zh: "执行标识" } satisfies BilingualLabel,
  identityEquivalent: { en: "Equivalent traces", zh: "等价追踪" } satisfies BilingualLabel,
  identityDriftVariants: { en: "Drift variants", zh: "偏差变体" } satisfies BilingualLabel,
  identityDrift: { en: "Identity drift", zh: "标识偏差" } satisfies BilingualLabel,
  noIdentity: { en: "No identity — query with engine v3", zh: "暂无标识信息，请使用 v3 引擎查询" } satisfies BilingualLabel,

  identityHeader: { en: "Identity Header", zh: "标识概览" } satisfies BilingualLabel,
  identityStability: { en: "Identity stability", zh: "标识稳定性" } satisfies BilingualLabel,
  identityDriftFlag: { en: "Drift", zh: "偏差" } satisfies BilingualLabel,
  equivalentCount: { en: "Equivalent traces", zh: "等价追踪数" } satisfies BilingualLabel,
  yes: { en: "YES", zh: "是" } satisfies BilingualLabel,
  no: { en: "NO", zh: "否" } satisfies BilingualLabel,
  traceInstance: { en: "Trace instance", zh: "追踪实例" } satisfies BilingualLabel,

  traceTimeline: { en: "Trace Timeline", zh: "执行时序" } satisfies BilingualLabel,
  causalSubgraph: { en: "Causal Subgraph", zh: "因果链路" } satisfies BilingualLabel,
  causalEdges: { en: "edges", zh: "关联" } satisfies BilingualLabel,
  stateDiffStream: { en: "State Diff Stream", zh: "状态变更" } satisfies BilingualLabel,

  identityPanelDetail: { en: "Identity Panel", zh: "标识详情" } satisfies BilingualLabel,
  sigGraph: { en: "graph_hash", zh: "图结构指纹" } satisfies BilingualLabel,
  sigState: { en: "state_hash", zh: "状态指纹" } satisfies BilingualLabel,
  sigControl: { en: "control_hash", zh: "管控指纹" } satisfies BilingualLabel,
  sigCausal: { en: "causal_hash", zh: "因果指纹" } satisfies BilingualLabel,
  identityExplanation: { en: "Identity explanation", zh: "标识说明" } satisfies BilingualLabel,
} satisfies Record<string, BilingualLabel>;

export const tokenL = {
  title: { en: "Token Observatory", zh: "算力观测" } satisfies BilingualLabel,
  consoleTitle: { en: "Token Observatory Console", zh: "算力观测台" } satisfies BilingualLabel,
  consoleSubtitle: {
    en: "Cost · Binding · Gravity Field · Influence · Identity",
    zh: "消耗统计 · 执行归因 · 热力分布 · 因果权重 · 执行标识",
  } satisfies BilingualLabel,
  loading: { en: "Loading Token Graph...", zh: "正在加载用量数据…" } satisfies BilingualLabel,
  totalTokens: { en: "Total Tokens", zh: "Token 总量" } satisfies BilingualLabel,
  tokensIn: { en: "Tokens In", zh: "输入量" } satisfies BilingualLabel,
  tokensOut: { en: "Tokens Out", zh: "输出量" } satisfies BilingualLabel,
  activeTraces: { en: "Active Traces", zh: "活跃追踪" } satisfies BilingualLabel,
  spikeCount: { en: "Spikes", zh: "突增次数" } satisfies BilingualLabel,
  highCostCount: { en: "High Cost", zh: "高消耗" } satisfies BilingualLabel,
  spikes: { en: "Token Spikes", zh: "消耗异常" } satisfies BilingualLabel,
  noAnomalies: { en: "No anomalies detected", zh: "未发现异常消耗" } satisfies BilingualLabel,
  distribution: { en: "Token Distribution", zh: "用量排行" } satisfies BilingualLabel,
  modeCostMap: { en: "Mode Cost Map", zh: "按模式统计" } satisfies BilingualLabel,
  gravityField: { en: "Token Cost Gravity Field", zh: "消耗热力分布" } satisfies BilingualLabel,
  totalCost: { en: "Total Cost", zh: "总消耗" } satisfies BilingualLabel,
  identityOverlay: { en: "Identity", zh: "执行标识" } satisfies BilingualLabel,
  costTimeline: { en: "Cost Timeline", zh: "消耗时序" } satisfies BilingualLabel,
  noFieldData: { en: "No token field data", zh: "暂无分布数据" } satisfies BilingualLabel,
  hotPaths: { en: "Hot Paths (token influence)", zh: "高消耗因果路径" } satisfies BilingualLabel,
  byPhase: { en: "By Phase", zh: "分阶段统计" } satisfies BilingualLabel,
  loadingField: { en: "Loading token field...", zh: "正在加载追踪数据…" } satisfies BilingualLabel,
  tabOverview: { en: "Overview", zh: "总览" } satisfies BilingualLabel,
  tabEvents: { en: "Events", zh: "消耗事件" } satisfies BilingualLabel,
  tabField: { en: "Field", zh: "热力分布" } satisfies BilingualLabel,
  tabBinding: { en: "Binding", zh: "执行归因" } satisfies BilingualLabel,
  tabInfluence: { en: "Influence", zh: "因果权重" } satisfies BilingualLabel,
  tabIdentity: { en: "Identity", zh: "执行标识" } satisfies BilingualLabel,
  tracePlaceholder: { en: "trace_id", zh: "输入 trace_id" } satisfies BilingualLabel,
  loadTrace: { en: "LOAD", zh: "查询" } satisfies BilingualLabel,
  refresh: { en: "Refresh", zh: "刷新" } satisfies BilingualLabel,
  traceList: { en: "Trace List", zh: "追踪列表" } satisfies BilingualLabel,
  traceCount: { en: "traces", zh: "条追踪" } satisfies BilingualLabel,
  noTraces: { en: "No traces", zh: "暂无追踪记录" } satisfies BilingualLabel,
  noEvents: { en: "No token events", zh: "暂无消耗事件" } satisfies BilingualLabel,
  noBindings: { en: "No bindings", zh: "暂无归因记录" } satisfies BilingualLabel,
  noHotPaths: { en: "No hot paths", zh: "暂无高消耗路径" } satisfies BilingualLabel,
  bindings: { en: "bindings", zh: "条归因" } satisfies BilingualLabel,
  weightedEdges: { en: "Weighted Causal Edges", zh: "加权因果链" } satisfies BilingualLabel,
  selectTrace: {
    en: "Select a trace from the list or enter trace_id",
    zh: "从左侧选择追踪，或输入 trace_id 查询",
  } satisfies BilingualLabel,
  selectEventHint: {
    en: "Click an event to inspect token binding",
    zh: "点击事件可查看消耗归因详情",
  } satisfies BilingualLabel,
  inspector: { en: "Token Inspector", zh: "事件详情" } satisfies BilingualLabel,
  whatHappened: { en: "What happened", zh: "消耗概况" } satisfies BilingualLabel,
  whoTriggered: { en: "Who triggered", zh: "触发来源" } satisfies BilingualLabel,
  whatChanged: { en: "What changed", zh: "关联执行" } satisfies BilingualLabel,
  dimension: { en: "Dimension", zh: "字段" } satisfies BilingualLabel,
  value: { en: "Value", zh: "数值" } satisfies BilingualLabel,
  identityCostBreakdown: { en: "Identity Cost Breakdown", zh: "分阶段消耗明细" } satisfies BilingualLabel,
  nodeCount: { en: "nodes", zh: "个节点" } satisfies BilingualLabel,
  maxWeight: { en: "max weight", zh: "最大权重" } satisfies BilingualLabel,
  consumedSummary: {
    en: "{source} used {total} tokens ({in} in / {out} out)",
    zh: "{source} 消耗 {total} Token（输入 {in} / 输出 {out}）",
  } satisfies BilingualLabel,
  boundToSpine: {
    en: "bound to spine event {id}",
    zh: "归因至脊柱事件 {id}",
  } satisfies BilingualLabel,
  boundEdge: { en: "causal edge {id}", zh: "因果边 {id}" } satisfies BilingualLabel,
  runtimeFallback: { en: "runtime", zh: "运行时" } satisfies BilingualLabel,
  traceSummary: { en: "trace", zh: "追踪" } satisfies BilingualLabel,
  eventsCount: { en: "events", zh: "事件数" } satisfies BilingualLabel,
  gradDelta: { en: "gradient", zh: "梯度" } satisfies BilingualLabel,
  weightShort: { en: "weight", zh: "权重" } satisfies BilingualLabel,
  severityHigh: { en: "HIGH", zh: "高" } satisfies BilingualLabel,
  severityMid: { en: "MEDIUM", zh: "中" } satisfies BilingualLabel,
  baseWeight: { en: "base", zh: "基准" } satisfies BilingualLabel,
  spineEvent: { en: "spine event", zh: "脊柱事件" } satisfies BilingualLabel,
  tokensInOut: { en: "in / out", zh: "输入 / 输出" } satisfies BilingualLabel,
  traceIoLine: {
    en: "{in} in · {out} out · {mode}",
    zh: "输入 {in} · 输出 {out} · {mode}",
  } satisfies BilingualLabel,
  eventSpineLine: {
    en: "spine {id} · {in} in / {out} out",
    zh: "脊柱事件 {id} · 输入 {in} / 输出 {out}",
  } satisfies BilingualLabel,
  hotPathWeight: {
    en: "weight {w} · {sev}",
    zh: "权重 {w} · {sev}",
  } satisfies BilingualLabel,
  edgeWeightLine: {
    en: "base {base} · weight {w}",
    zh: "基准 {base} · 权重 {w}",
  } satisfies BilingualLabel,
} satisfies Record<string, BilingualLabel>;

export const navL = {
  executionSpine: { en: "Execution Spine", zh: "执行观测" } satisfies BilingualLabel,
  executionSpineSub: {
    en: "Identity · Trace · Causal · State",
    zh: "标识 · 追踪 · 因果 · 状态",
  } satisfies BilingualLabel,
  debuggerLegacy: { en: "Debugger (legacy)", zh: "旧版调试器" } satisfies BilingualLabel,
  debuggerSub: {
    en: "GTBS projection fallback",
    zh: "GTBS 兼容视图",
  } satisfies BilingualLabel,
  flow: { en: "Neural Flow", zh: "记忆流图" } satisfies BilingualLabel,
  flowSub: { en: "Factor chain graph", zh: "关联网络" } satisfies BilingualLabel,
  workbench: { en: "Workbench", zh: "工作台" } satisfies BilingualLabel,
  workbenchSub: {
    en: "Chat · Suggestions · Upload",
    zh: "对话 · 建议 · 上传",
  } satisfies BilingualLabel,
  summaryMode: { en: "Value Summary", zh: "运行摘要" } satisfies BilingualLabel,
  summaryModeSub: {
    en: "CSE narrative · runtime pulse",
    zh: "CSE 叙事 · 运行脉搏",
  } satisfies BilingualLabel,
  summaryHint: {
    en: "Auto-synthesized runtime summary from CSE",
    zh: "CSE 自动归纳的运行摘要与观测卡片",
  } satisfies BilingualLabel,
  summaryPageTitle: { en: "CNexus Value Summary", zh: "CNexus 运行摘要" } satisfies BilingualLabel,
  summaryPageHint: {
    en: "Narrative summary · goal · identity · belief · focus",
    zh: "叙事摘要 · 目标 · 身份 · 信念 · 工作焦点",
  } satisfies BilingualLabel,
  learnMode: { en: "Learn Mode", zh: "认知教学" } satisfies BilingualLabel,
  learnModeSub: {
    en: "Human narrative",
    zh: "人类叙事",
  } satisfies BilingualLabel,
  learnHint: {
    en: "Turn ExecutionRecord into beginner-friendly AI behavior stories",
    zh: "把 ExecutionRecord 翻译成初学者能理解的 AI 行为故事",
  } satisfies BilingualLabel,
  learnPageTitle: { en: "CNexus Learn Mode", zh: "CNexus 认知教学" } satisfies BilingualLabel,
  learnPageHint: {
    en: "Beginner · intermediate · expert views from one trace",
    zh: "初学者 · 进阶 · 工程视角，基于单次执行记录",
  } satisfies BilingualLabel,
  debuggerHint: {
    en: "Legacy GTBS projection — prefer Learn Mode",
    zh: "旧版视图，建议使用认知教学",
  } satisfies BilingualLabel,
  debuggerTitle: { en: "CNexus Debugger (legacy)", zh: "CNexus 旧版调试器" } satisfies BilingualLabel,
  debuggerPageHint: {
    en: "GTBS fallback — not truth source",
    zh: "GTBS 兼容层，非权威数据源",
  } satisfies BilingualLabel,
  runtimeReader: { en: "Cognitive execution reader", zh: "运行时观测" } satisfies BilingualLabel,

  demoMode: { en: "Demo mode", zh: "演示模式" } satisfies BilingualLabel,
  connectedRuntime: { en: "Runtime connected", zh: "运行时已连接" } satisfies BilingualLabel,
  notConnected: { en: "Not connected", zh: "未连接" } satisfies BilingualLabel,
  warmingUp: { en: "Starting…", zh: "正在启动" } satisfies BilingualLabel,
  systemHealth: { en: "System health", zh: "系统状态" } satisfies BilingualLabel,
  views: { en: "Views", zh: "视图" } satisfies BilingualLabel,
  quickActions: { en: "Quick actions", zh: "快捷操作" } satisfies BilingualLabel,
  refresh: { en: "Refresh", zh: "刷新" } satisfies BilingualLabel,
  switchDataSource: { en: "Switch data source", zh: "切换数据源" } satisfies BilingualLabel,

  flowHint: {
    en: "Memory factor chain · Obsidian-style graph view",
    zh: "记忆关联网络 · 图谱视图",
  } satisfies BilingualLabel,
  workbenchHint: {
    en: "Chat with the system, view suggestions, and upload files",
    zh: "系统对话、今日建议与文件上传",
  } satisfies BilingualLabel,
  workbenchOffline: {
    en: "Runtime not connected — start API or switch to Demo",
    zh: "未连接运行时，请先启动 API 或切换演示模式",
  } satisfies BilingualLabel,
  workbenchWarming: {
    en: "Runtime is starting — chat, suggestions, and upload unlock when fully ready",
    zh: "Runtime 正在启动，完全就绪后可对话、查看建议与上传",
  } satisfies BilingualLabel,

  flowPageTitle: { en: "CNexus Neural Flow", zh: "CNexus 记忆流图" } satisfies BilingualLabel,
  flowPageHint: {
    en: "Factor chain · Graph view · Adjustable forces",
    zh: "关联网络 · 力导向图 · 参数可调",
  } satisfies BilingualLabel,
  workbenchPageTitle: { en: "CNexus Workbench", zh: "CNexus 工作台" } satisfies BilingualLabel,
  workbenchDemoHint: { en: "Demo", zh: "演示数据" } satisfies BilingualLabel,
  workbenchConnectedHint: { en: "Connected", zh: "已连接" } satisfies BilingualLabel,
  workbenchOfflineHint: { en: "Not connected", zh: "未连接" } satisfies BilingualLabel,

  tokenObservatory: { en: "Token Observatory", zh: "算力观测" } satisfies BilingualLabel,
  tokenObservatorySub: {
    en: "Console · Events · Field · Influence",
    zh: "总览 · 事件 · 分布 · 归因",
  } satisfies BilingualLabel,
  tokenPageTitle: { en: "CNexus Token Observatory", zh: "CNexus 算力观测" } satisfies BilingualLabel,
  tokenPageHint: {
    en: "Token cost physics · binding · gravity field · causal influence",
    zh: "消耗归因 · 热力分布 · 因果权重 · 执行标识对照",
  } satisfies BilingualLabel,

  debuggerHeader: { en: "CNexus Debugger", zh: "CNexus 调试器" } satisfies BilingualLabel,
  debuggerHeaderSub: {
    en: "Event Spine · Causal Graph · Control + State Inspector",
    zh: "事件流 · 因果图 · 管控与状态",
  } satisfies BilingualLabel,
} satisfies Record<string, BilingualLabel>;

export const homeL = {
  valueSummary: { en: "Value Summary", zh: "运行摘要" } satisfies BilingualLabel,
  example: { en: "Example", zh: "示例" } satisfies BilingualLabel,
  valueLoadError: { en: "Failed to load value summary", zh: "摘要加载失败" } satisfies BilingualLabel,
  valueEmptyLive: {
    en: "Connect Runtime and use Ask, Capture, or Analyze to build a summary.",
    zh: "连接运行时后，通过提问、记录或分析，系统会自动归纳运行摘要",
  } satisfies BilingualLabel,
  valueEmptyIdle: {
    en: "No summary yet — it will appear as you use the system.",
    zh: "暂无摘要，使用系统后会自动生成",
  } satisfies BilingualLabel,
  neuralFlow: { en: "Neural Flow", zh: "记忆流图" } satisfies BilingualLabel,
  neuralFlowSub: {
    en: "Graph view · force-directed memory network",
    zh: "力导向记忆网络 · 中心簇与外环 · 右侧可调参数",
  } satisfies BilingualLabel,
  dashboard: { en: "Dashboard", zh: "运行面板" } satisfies BilingualLabel,
  sync: { en: "Sync", zh: "同步" } satisfies BilingualLabel,
  recentPulse: { en: "Recent pulse", zh: "最近动态" } satisfies BilingualLabel,
  graphEmpty: {
    en: "No nodes yet — write memory to build the graph",
    zh: "暂无节点，写入记忆后将生成图谱",
  } satisfies BilingualLabel,
  graphTitle: { en: "Neural flow · memory factor network", zh: "记忆流图 · 关联网络" } satisfies BilingualLabel,
  tabTrace: { en: "Trace log", zh: "运行记录" } satisfies BilingualLabel,
  tabSettings: { en: "Runtime mode", zh: "运行模式" } satisfies BilingualLabel,
  tabModel: { en: "Model API", zh: "大模型 API" } satisfies BilingualLabel,
  traceStats: {
    en: "{logs} events · {traces} traces",
    zh: "共 {logs} 条事件 · {traces} 条追踪",
  } satisfies BilingualLabel,
  refreshing: { en: "Refreshing…", zh: "刷新中…" } satisfies BilingualLabel,
  noTraceLogs: { en: "No trace logs yet", zh: "暂无运行记录" } satisfies BilingualLabel,
  logLevelError: { en: "Error", zh: "错误" } satisfies BilingualLabel,
  logLevelWarn: { en: "Warn", zh: "警告" } satisfies BilingualLabel,
  logLevelOk: { en: "OK", zh: "正常" } satisfies BilingualLabel,
  runtimeModeHint: {
    en: "Pick a runtime mode for your machine (local config, safe to revert)",
    zh: "选择适合本机的运行模式（本地配置，可随时改回）",
  } satisfies BilingualLabel,
  concurrencyMax: { en: "Concurrency (max 2)", zh: "并发数（最大 2）" } satisfies BilingualLabel,
  autoSynth: { en: "Auto-update cognitive summary", zh: "自动更新认知结论" } satisfies BilingualLabel,
} satisfies Record<string, BilingualLabel>;

export const footerL = {
  dataFlowGuide: { en: "Data flow", zh: "数据流向" } satisfies BilingualLabel,
  chatFlow: {
    en: "Chat → Goal/Belief/Memory → Reflection",
    zh: "对话流：对话 → 目标/信念/记忆 → 反思",
  } satisfies BilingualLabel,
  browseFlow: {
    en: "Memory → Identity/Goal/Belief → Governance",
    zh: "浏览流：记忆 → 身份/目标/信念 → 治理",
  } satisfies BilingualLabel,
  importFlow: {
    en: "Upload → Episodic → Synthesis → Goal Layer",
    zh: "导入流：上传 → 情景记忆 → 综合 → 目标层",
  } satisfies BilingualLabel,
  corePrinciples: { en: "Core principles", zh: "核心设计原则" } satisfies BilingualLabel,
  p4Loop: { en: "P4 closed loop", zh: "P4 闭环支撑" } satisfies BilingualLabel,
  health: { en: "health", zh: "健康" } satisfies BilingualLabel,
} satisfies Record<string, BilingualLabel>;

export const bootL = {
  config: { en: "Loading config", zh: "加载配置" } satisfies BilingualLabel,
  hydrating: { en: "Starting", zh: "正在启动" } satisfies BilingualLabel,
  sync: { en: "Connecting runtime", zh: "连接运行时" } satisfies BilingualLabel,
  runtimeStarting: { en: "Starting runtime…", zh: "正在启动运行时…" } satisfies BilingualLabel,
  floatPending: { en: "Preparing float bar", zh: "准备悬浮条" } satisfies BilingualLabel,
  float: { en: "Ready", zh: "就绪" } satisfies BilingualLabel,
  degraded: { en: "Degraded mode", zh: "降级模式" } satisfies BilingualLabel,
  runtimeBundleMissing: {
    en: "Runtime bundle missing — run bundle:runtime",
    zh: "未找到 Runtime 包 — 请先执行 bundle:runtime",
  } satisfies BilingualLabel,
  runtimeInitFailed: { en: "Runtime init failed", zh: "Runtime 初始化失败" } satisfies BilingualLabel,
  runtimeSpawnFailed: { en: "Failed to start runtime process", zh: "无法启动 Runtime 进程" } satisfies BilingualLabel,
  initProduct: { en: "Starting CNexus…", zh: "正在启动 CNexus…" } satisfies BilingualLabel,
} satisfies Record<string, BilingualLabel>;

export const floatL = {
  factorGraph: { en: "Factor network", zh: "因子词网络" } satisfies BilingualLabel,
  factorGraphHint: {
    en: "Force-directed · same graph as main window",
    zh: "力导向 · 与大窗同源",
  } satisfies BilingualLabel,
  tokenStrip: { en: "Token usage", zh: "算力消耗" } satisfies BilingualLabel,
  tokenEmpty: { en: "No token data yet", zh: "暂无消耗数据" } satisfies BilingualLabel,
  tokenEmptyLive: {
    en: "Runtime live — no token usage yet. Send a chat message to record costs.",
    zh: "运行时已连接，暂无 Token 消耗。发送一条对话后即可显示。",
  } satisfies BilingualLabel,
  tokenOffline: {
    en: "Connect Runtime to load token usage",
    zh: "请先连接运行时以加载 Token 数据",
  } satisfies BilingualLabel,
  tokenLoading: { en: "Loading…", zh: "加载中…" } satisfies BilingualLabel,
  openTokenConsole: { en: "Open Token Observatory", zh: "打开算力观测" } satisfies BilingualLabel,
  importPanel: { en: "Import memory", zh: "导入记忆" } satisfies BilingualLabel,
} satisfies Record<string, BilingualLabel>;

export const debuggerL = {
  selectEvent: {
    en: "Select an event in Timeline or Graph",
    zh: "请在时序或图谱中选择事件",
  } satisfies BilingualLabel,
  inspectHint: {
    en: "View Control · Intent · State Diff",
    zh: "查看管控、意图与状态变更",
  } satisfies BilingualLabel,
  noSpineEvents: {
    en: "No Spine events — connect Runtime or switch Demo",
    zh: "暂无脊柱事件，请连接运行时或切换演示模式",
  } satisfies BilingualLabel,
  noSpineEventsLive: {
    en: "Runtime is live — no GTBS events yet. Send a chat message or run Analyze to generate traces.",
    zh: "运行时已连接，暂无脊柱事件。发送对话或点击分析以生成追踪。",
  } satisfies BilingualLabel,
  spineOffline: {
    en: "Runtime not connected — connect services or switch Demo",
    zh: "运行时未连接 — 请连接服务或切换演示模式",
  } satisfies BilingualLabel,
  waitForTrace: {
    en: "Select a trace or wait for events",
    zh: "请选择追踪或等待事件",
  } satisfies BilingualLabel,
  causalProjection: {
    en: "parent_event_id · causal_links projection",
    zh: "基于 parent_event_id 与 causal_links 投影",
  } satisfies BilingualLabel,
} satisfies Record<string, BilingualLabel>;

export const connectionL = {
  ollamaRunning: { en: "Ollama running", zh: "Ollama 已运行" } satisfies BilingualLabel,
  ollamaConnected: { en: "Ollama connected", zh: "Ollama 已连接" } satisfies BilingualLabel,
  ollamaDisconnected: { en: "Ollama not connected", zh: "Ollama 未连接" } satisfies BilingualLabel,
  ollamaStopped: { en: "Ollama not started", zh: "Ollama 未启动" } satisfies BilingualLabel,
  ollamaMissing: { en: "Ollama not installed", zh: "未安装 Ollama" } satisfies BilingualLabel,
  ollamaLocal: { en: "Ollama running (local)", zh: "Ollama 已运行（本机）" } satisfies BilingualLabel,
  ollamaNotFound: { en: "Ollama not detected", zh: "未检测到 Ollama" } satisfies BilingualLabel,
  ollamaProbing: { en: "Detecting Ollama…", zh: "正在检测 Ollama…" } satisfies BilingualLabel,
  runtimeStartHint: {
    en: "Run in terminal: python -m api.main (port 8000)",
    zh: "请在终端执行：python -m api.main（端口 8000）",
  } satisfies BilingualLabel,
  runtimeNotReadyDev: {
    en: "Runtime not ready. Start API in brain-memory-ui, or restart CNexus.",
    zh: "运行时未就绪。请在 brain-memory-ui 目录启动 API，或重启 CNexus",
  } satisfies BilingualLabel,
  runtimeNotReadyLocal: {
    en: "Runtime not ready. Ensure 127.0.0.1:8000 is running.",
    zh: "运行时未就绪，请确认本机 127.0.0.1:8000 已启动",
  } satisfies BilingualLabel,
  connectRuntimeFirst: {
    en: "Connect Runtime before starting Ollama via API.",
    zh: "请先连接运行时，再通过 API 启动 Ollama",
  } satisfies BilingualLabel,
  runtimeConnected: { en: "Runtime connected", zh: "运行时已连接" } satisfies BilingualLabel,
  runtimeConnectedSuccess: {
    en: "Runtime connected — closing panel…",
    zh: "运行时已连接，正在关闭…",
  } satisfies BilingualLabel,
  runtimeConnecting: { en: "Connecting…", zh: "正在连接…" } satisfies BilingualLabel,
  runtimeWarming: { en: "Runtime starting…", zh: "正在启动…" } satisfies BilingualLabel,
  runtimeDisconnected: { en: "Runtime disconnected", zh: "运行时未连接" } satisfies BilingualLabel,
  connectServices: { en: "Connect services", zh: "连接服务" } satisfies BilingualLabel,
  localServices: { en: "Local services", zh: "本地服务" } satisfies BilingualLabel,
  localServicesSub: { en: "Runtime API · Ollama", zh: "运行时 API · Ollama 模型" } satisfies BilingualLabel,
  reconnectRuntime: { en: "Probe Runtime", zh: "重新探测运行时" } satisfies BilingualLabel,
  connectRuntime: { en: "Connect Runtime", zh: "连接运行时" } satisfies BilingualLabel,
  ollamaOfflineProbe: {
    en: "Runtime offline — local port probe only",
    zh: "运行时离线，仅探测本机端口",
  } satisfies BilingualLabel,
  ollamaAlreadyRunning: { en: "Ollama already running", zh: "Ollama 已在运行" } satisfies BilingualLabel,
  ollamaStarting: { en: "Starting…", zh: "正在启动…" } satisfies BilingualLabel,
  startOllama: { en: "Start Ollama", zh: "启动 Ollama" } satisfies BilingualLabel,
  ollamaNeedsRuntime: {
    en: "Port 11434 responds, but Runtime is required for chat and embeddings.",
    zh: "11434 端口有响应，但对话与向量需先连接运行时",
  } satisfies BilingualLabel,
  devSidecarHint: {
    en: "Dev mode won't auto-start sidecar. Run API manually in brain-memory-ui.",
    zh: "开发模式不会自动拉起 sidecar，请在 brain-memory-ui 目录手动启动 API",
  } satisfies BilingualLabel,
} satisfies Record<string, BilingualLabel>;
