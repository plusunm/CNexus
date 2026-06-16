"use client";

import { useMemo, useRef } from "react";
import { GitBranch } from "lucide-react";
import { useMindOverview } from "@/cnexus-kernel";
import { useFloatFactorGraphFrame } from "@/hooks/useFloatFactorGraphFrame";
import { buildFactorGraph } from "@/lib/factorGraphModel";
import { floatTy } from "@/lib/floatTypography";
import { useFloatingBarStore } from "@/lib/floatingBarStore";
import { bi, floatL } from "@/lib/spine/labels";
import { useMindTheme } from "../MindUiProvider";
import { GraphViewCanvas } from "../home/GraphViewCanvas";
import { FloatTokenStrip, useFloatTokenTraces } from "./FloatTokenStrip";

/** 悬浮窗记忆页 — 上：因子词网络（与大窗 GraphView 同源）；下：Token 消耗 */
export function FloatingMemoryPanel() {
  const t = useMindTheme();
  const stage = useFloatingBarStore((s) => s.stage);
  const sessionEpoch = useFloatingBarStore((s) => s.sessionEpoch);
  const panelRef = useRef<HTMLDivElement>(null);
  const frame = useFloatFactorGraphFrame(stage, panelRef);
  const { overview } = useMindOverview();
  const factorGraph = useMemo(() => buildFactorGraph(overview), [overview]);
  const token = useFloatTokenTraces();

  return (
    <div
      ref={panelRef}
      className="cnexus-float-panel min-h-0 min-w-0 overflow-hidden h-full"
      style={{
        backgroundColor: t.surface,
        borderColor: t.border,
        display: "grid",
        gridTemplateRows: `auto ${frame.graphSlotHeight}px minmax(${frame.tokenAreaHeight}px, 1fr)`,
      }}
      data-cnexus-float-memory
    >
      <div
        className="shrink-0 flex items-center gap-1.5 px-2.5 py-1.5 border-b"
        style={{ borderColor: t.border }}
        data-cnexus-float-factor-header
        data-no-drag
      >
        <GitBranch className="w-3.5 h-3.5" style={{ color: t.purple }} />
        <span className={floatTy.label} style={{ color: t.text }}>
          {bi(floatL.factorGraph)}
        </span>
        <span className={`${floatTy.mono} ml-auto`} style={{ color: t.textMuted }}>
          {factorGraph.nodes.length}
        </span>
      </div>

      <div
        className="shrink-0 w-full min-w-0 overflow-hidden px-2 pt-2 pb-1"
        style={{ height: frame.graphSlotHeight }}
        data-no-drag
        data-cnexus-float-factor-graph
      >
        <GraphViewCanvas
          graph={factorGraph}
          compact
          layoutKey={`${stage}-${sessionEpoch}`}
          frame={{ width: frame.graphWidth, height: frame.graphHeight }}
        />
      </div>

      <div className="min-h-0 flex flex-col overflow-hidden" style={{ minHeight: frame.tokenAreaHeight }}>
        <FloatTokenStrip
          traces={token.traces}
          loading={token.loading}
          error={token.error}
          traceMaxHeight={frame.tokenTraceHeight}
          isLive={token.isLive}
          emptyHint={token.emptyHint}
          onRefresh={() => void token.refresh()}
        />
      </div>
    </div>
  );
}
