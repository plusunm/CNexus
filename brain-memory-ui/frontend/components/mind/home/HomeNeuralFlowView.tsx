"use client";



import { useEffect, useMemo, useState } from "react";

import Link from "next/link";

import { ArrowLeft, RefreshCw, Zap } from "lucide-react";

import type { CognitiveOutput, ExecLogEvent, ExecTraceManifest } from "@/lib/cognitiveTypes";

import { useMindOverview } from "@/cnexus-kernel";

import { buildDataFlowModel, FLOW_STREAM_META } from "@/lib/dataFlowModel";

import { buildFactorGraph } from "@/lib/factorGraphModel";
import { bi, biSection, homeL } from "@/lib/spine/labels";
import { useMindTheme } from "../MindUiProvider";

import { GraphViewCanvas } from "./GraphViewCanvas";



type Props = {

  data: CognitiveOutput;

  logs: ExecLogEvent[];

  traces: ExecTraceManifest[];

  loading: boolean;

  refreshing?: boolean;

  onRefresh: () => void;

};



/** 神经数据流 — Obsidian 式 Graph view（力导向 + 右侧控制栏） */

export function HomeNeuralFlowView({ data, logs, traces, loading, refreshing, onRefresh }: Props) {

  const t = useMindTheme();

  const { overview, isDemo } = useMindOverview();

  const [tick, setTick] = useState(0);



  useEffect(() => {

    const id = window.setInterval(() => setTick((n) => n + 1), 1200);

    return () => window.clearInterval(id);

  }, []);



  const model = useMemo(

    () =>

      buildDataFlowModel({

        logs,

        traces,

        data,

        overview,

        isDemo,

        tick,

      }),

    [logs, traces, data, overview, isDemo, tick],

  );



  const factorGraph = useMemo(() => buildFactorGraph(overview), [overview]);



  return (

    <div className="space-y-4 w-full min-w-0 max-w-none">

      <header className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">

        <div>

          <div className="flex items-center gap-2 flex-wrap">

            <Zap className="w-5 h-5" style={{ color: t.purple }} />

            <h1 className="text-xl font-bold" style={{ color: t.text }}>
              {biSection(homeL.neuralFlow)}
            </h1>
          </div>
          <p className="text-sm mt-1" style={{ color: t.textMuted }}>
            {bi(homeL.neuralFlowSub)}
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">

          <Link

            href="/shell?layout=overview&view=classic"

            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] border"

            style={{ borderColor: t.border, color: t.textMuted }}

          >

            <ArrowLeft className="w-3.5 h-3.5" />

            {bi(homeL.dashboard)}

          </Link>

          <button

            type="button"

            onClick={onRefresh}

            disabled={loading}

            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] border disabled:opacity-50"

            style={{ borderColor: t.blue, color: t.blue, backgroundColor: t.blueSoft }}

          >

            <RefreshCw className={`w-3.5 h-3.5 ${loading || refreshing ? "animate-spin" : ""}`} />

            {bi(homeL.sync)}

          </button>

        </div>

      </header>



      <GraphViewCanvas graph={factorGraph} />



      {model.pulses.length > 0 && (

        <div

          className="rounded-xl border px-4 py-3 flex flex-wrap gap-2 text-[10px]"

          style={{ borderColor: t.border, backgroundColor: t.surface, color: t.textMuted }}

        >

          <span className="w-full text-xs font-medium mb-1" style={{ color: t.text }}>

            {bi(homeL.recentPulse)}

          </span>

          {model.pulses.slice(0, 6).map((pulse) => {

            const meta = FLOW_STREAM_META[pulse.stream];

            const color =

              meta.themeKey === "green"

                ? t.green

                : meta.themeKey === "blue"

                  ? t.blue

                  : meta.themeKey === "orange"

                    ? t.orange

                    : t.purple;

            return (

              <span

                key={pulse.id}

                className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full border"

                style={{ borderColor: t.border }}

              >

                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: color }} />

                {pulse.text}

              </span>

            );

          })}

        </div>

      )}

    </div>

  );

}


