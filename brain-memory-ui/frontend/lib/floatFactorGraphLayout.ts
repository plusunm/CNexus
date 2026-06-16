import type { FloatStage } from "./floatingBarStorage";
import { floatShellHeight, floatShellWidth } from "./floatWindowSpec";

/**
 * Chrome heights (px) derived from float shell Tailwind classes.
 * Keep in sync with FloatingHeaderBar, FloatingQuickButtons, FloatingCognitiveHints,
 * FloatingExpandPanel, FloatingMemoryPanel, FloatTokenStrip.
 */
export const FLOAT_SHELL_CHROME = {
  /** FloatingHeaderBar — px-3 py-2 border-b */
  headerBar: 44,
  /** FloatingQuickButtons — px-3 py-2 + tab py-2 */
  quickTabs: 48,
  /** FloatingCognitiveHints — pt-2 pb-1.5 + badge + suggestion row */
  cognitiveHints: 76,
  /** FloatingExpandPanel content — pb-3 */
  expandPadBottom: 12,
  /** FloatingExpandPanel content — px-3 × 2 */
  expandPadX: 24,
} as const;

export const FLOAT_MEMORY_PANEL_CHROME = {
  /** Section header — py-1.5 + 12px label */
  sectionHeader: 32,
  /** Graph wrapper — px-2 × 2 */
  graphPadX: 16,
  graphPadTop: 8,
  graphPadBottom: 4,
  /** GraphViewCanvas compact border */
  graphBorder: 2,
  /** Compact footer — factorGraphHint + node count */
  graphFooter: 16,
  /** FloatTokenStrip fixed chrome (header + stats) before trace list */
  tokenStripFixed: 82,
  tokenTraceMin: 72,
  tokenTraceMax: 140,
} as const;

/** Share of memory-panel body (below section header) reserved for the factor graph. */
const GRAPH_BODY_SHARE: Record<FloatStage, number> = {
  expanded: 0.56,
  bar: 0.5,
  dock: 0.45,
};

const GRAPH_HEIGHT_BOUNDS: Record<FloatStage, { min: number; max: number }> = {
  expanded: { min: 220, max: 340 },
  bar: { min: 160, max: 200 },
  dock: { min: 120, max: 160 },
};

export type FloatFactorGraphFrame = {
  shellWidth: number;
  shellHeight: number;
  memoryPanelHeight: number;
  graphWidth: number;
  graphHeight: number;
  /** graphHeight + vertical padding + border — grid row size */
  graphSlotHeight: number;
  tokenTraceHeight: number;
  tokenAreaHeight: number;
};

function memoryPanelHeightForStage(stage: FloatStage): number {
  const shellH = floatShellHeight(stage);
  const c = FLOAT_SHELL_CHROME;
  const expandBody = shellH - c.headerBar - c.quickTabs;
  return expandBody - c.cognitiveHints - c.expandPadBottom;
}

export function computeFloatFactorGraphFrame(stage: FloatStage): FloatFactorGraphFrame {
  const shellW = floatShellWidth(stage);
  const shellH = floatShellHeight(stage);
  const shell = FLOAT_SHELL_CHROME;
  const mem = FLOAT_MEMORY_PANEL_CHROME;
  const bounds = GRAPH_HEIGHT_BOUNDS[stage];

  const memoryPanelH = memoryPanelHeightForStage(stage);
  const bodyBelowHeader = Math.max(0, memoryPanelH - mem.sectionHeader);
  const graphChrome = mem.graphPadTop + mem.graphPadBottom + mem.graphBorder + mem.graphFooter;
  const tokenMinArea = mem.tokenStripFixed + mem.tokenTraceMin;
  const maxGraphCanvas = Math.max(0, bodyBelowHeader - tokenMinArea - graphChrome);

  let graphHeight = Math.floor(bodyBelowHeader * GRAPH_BODY_SHARE[stage]) - graphChrome;
  graphHeight = Math.max(
    Math.min(bounds.min, maxGraphCanvas),
    Math.min(bounds.max, graphHeight, maxGraphCanvas),
  );

  let tokenAreaHeight = bodyBelowHeader - graphHeight - graphChrome;
  let tokenTraceH = tokenAreaHeight - mem.tokenStripFixed;
  tokenTraceH = Math.max(mem.tokenTraceMin, Math.min(mem.tokenTraceMax, tokenTraceH));
  tokenAreaHeight = mem.tokenStripFixed + tokenTraceH;

  const used = graphHeight + graphChrome + tokenAreaHeight;
  if (used > bodyBelowHeader) {
    const excess = used - bodyBelowHeader;
    tokenTraceH = Math.max(mem.tokenTraceMin, tokenTraceH - excess);
    tokenAreaHeight = mem.tokenStripFixed + tokenTraceH;
    graphHeight = Math.max(0, bodyBelowHeader - graphChrome - tokenAreaHeight);
  }

  const graphSlotHeight = graphHeight + graphChrome;
  const graphWidth = Math.max(160, shellW - shell.expandPadX - mem.graphPadX);

  return {
    shellWidth: shellW,
    shellHeight: shellH,
    memoryPanelHeight: memoryPanelH,
    graphWidth,
    graphHeight,
    graphSlotHeight,
    tokenTraceHeight: tokenTraceH,
    tokenAreaHeight,
  };
}

/** Refine theoretical frame using measured panel + section header (token area stays reserved). */
export function refineFloatFactorGraphFrame(
  stage: FloatStage,
  panelWidth: number,
  panelHeight: number,
  headerHeight: number,
  base: FloatFactorGraphFrame,
): FloatFactorGraphFrame {
  const mem = FLOAT_MEMORY_PANEL_CHROME;
  const bounds = GRAPH_HEIGHT_BOUNDS[stage];

  if (panelWidth < 1 || panelHeight < 1) return base;

  const graphChrome = mem.graphPadTop + mem.graphPadBottom + mem.graphBorder + mem.graphFooter;
  const graphWidth = Math.max(160, panelWidth - mem.graphPadX);
  const rawGraphH = panelHeight - headerHeight - base.tokenAreaHeight - graphChrome;
  const graphHeight = Math.max(
    Math.min(bounds.min, rawGraphH),
    Math.min(bounds.max, rawGraphH),
  );
  const graphSlotHeight = graphHeight + graphChrome;

  return {
    ...base,
    memoryPanelHeight: panelHeight,
    graphWidth,
    graphHeight,
    graphSlotHeight,
  };
}
