"use client";



import { useEffect, useState } from "react";

import { useSearchParams } from "next/navigation";

import { RefreshCw } from "lucide-react";

import { useMindOverview } from "@/cnexus-kernel";

import { parseOverviewView } from "@/cnexus-kernel/shellTypes";

import { MindModeSwitch } from "../MindModeSwitch";

import { useMindConnection } from "../MindConnectionProvider";

import { useMindTheme } from "../MindUiProvider";

import { useCognitiveSynthesis } from "@/hooks/useCognitiveSynthesis";

import { useExecTrace } from "@/hooks/useExecTrace";

import { useCnexusConfigStore } from "@/lib/cnexusConfigStore";
import { CSE_POLL_MS } from "@/lib/uiPollIntervals";

import { getCognitiveSourceMeta } from "@/lib/cognitiveSource";

import { HomeSidebar } from "./HomeSidebar";

import { ValueSummaryLayout } from "./ValueSummaryLayout";

import { WorkbenchLayout } from "./WorkbenchLayout";

import { DebuggerLayout } from "../debugger/DebuggerLayout";

import { TokenConsoleLayout } from "../token/TokenConsoleLayout";

import { LearnConsoleLayout } from "../learn/LearnConsoleLayout";

import { bi, biSection, navL } from "@/lib/spine/labels";

import { HomeNeuralFlowView } from "./HomeNeuralFlowView";

import type { IntentMode } from "@/lib/cognitiveTypes";



export default function HomeMindLayout() {

  const t = useMindTheme();

  const params = useSearchParams();

  const activeView = parseOverviewView(params.get("view"));

  const { disconnect, effectiveMode } = useMindConnection();

  const { isDemo, isLive, isWarming } = useMindOverview();

  const sourceMeta = getCognitiveSourceMeta(effectiveMode);

  const cseWindow = useCnexusConfigStore((s) => s.config.cse.window_size);

  const autoSynth = useCnexusConfigStore((s) => s.config.cse.enabled && s.config.cse.auto_synthesize);

  const pollMs = autoSynth && effectiveMode === "runtime" ? CSE_POLL_MS : 0;

  const { data, loading, refreshing, error, refresh, synthesize } = useCognitiveSynthesis(pollMs);

  const {
    logs,
    traces,
    loading: traceLoading,
    refreshing: traceRefreshing,
    refresh: refreshTrace,
  } = useExecTrace(80);

  const [intentResult, setIntentResult] = useState<string | null>(null);

  const isEmpty = !sourceMeta.isExample && !data.summary.length && !data.insights.length;



  useEffect(() => {

    setIntentResult(null);

  }, [effectiveMode]);



  const handleRefresh = () => void refresh(cseWindow);



  const pageTitle =

    activeView === "learn"

      ? biSection(navL.learnPageTitle)

      : activeView === "summary"

        ? biSection(navL.summaryPageTitle)

      : activeView === "workbench"

        ? biSection(navL.workbenchPageTitle)

      : activeView === "debugger"

        ? biSection(navL.debuggerTitle)

      : activeView === "flow"

        ? biSection(navL.flowPageTitle)

      : activeView === "token"

        ? biSection(navL.tokenPageTitle)

        : biSection(navL.learnPageTitle);

  const pageHint =

    activeView === "learn"

      ? biSection(navL.learnPageHint)

      : activeView === "summary"

        ? biSection(navL.summaryPageHint)

      : activeView === "workbench"

        ? isDemo

          ? bi(navL.workbenchDemoHint)

          : isLive

            ? bi(navL.workbenchConnectedHint)

            : isWarming

              ? bi(navL.warmingUp)

              : bi(navL.workbenchOfflineHint)

      : activeView === "debugger"

        ? biSection(navL.debuggerPageHint)

      : activeView === "flow"

        ? biSection(navL.flowPageHint)

      : activeView === "token"

        ? biSection(navL.tokenPageHint)

        : biSection(navL.learnPageHint);



  return (

    <div

      className="min-h-screen flex"

      style={{

        backgroundColor: t.bg,

        color: t.text,

        backgroundImage: `radial-gradient(ellipse at 100% 0%, ${t.purpleSoft} 0%, transparent 40%), radial-gradient(ellipse at 0% 100%, ${t.blueSoft} 0%, transparent 35%)`,

      }}

    >

      <HomeSidebar

        onRefresh={handleRefresh}

        loading={loading || refreshing}

        activeView={activeView}

      />



      <div className="flex-1 flex flex-col min-w-0">

        <header

          className="lg:hidden flex items-center justify-between px-4 py-3 border-b shrink-0"

          style={{ borderColor: t.border, backgroundColor: t.surface }}

        >

          <div>

            <p className="text-sm font-semibold" style={{ color: t.text }}>{pageTitle}</p>

            <p className="text-[11px]" style={{ color: t.textMuted }}>{pageHint}</p>

          </div>

          <div className="flex items-center gap-2">

            <button
              type="button"
              onClick={handleRefresh}
              disabled={loading || refreshing}
              aria-busy={loading || refreshing}
              className="p-2 rounded-lg border disabled:opacity-50 transition-transform active:scale-95"
              style={{ borderColor: t.border }}
            >

              <RefreshCw className={`w-4 h-4 ${loading || refreshing ? "animate-spin" : ""}`} />

            </button>

            <MindModeSwitch compact />

          </div>

        </header>



        <main className="flex-1 overflow-auto w-full py-4 lg:py-5 pl-3 pr-4 lg:pl-4 lg:pr-6 max-w-none">

          {activeView === "debugger" ? (

            <DebuggerLayout />

          ) : activeView === "flow" ? (

            <HomeNeuralFlowView

              data={data}

              logs={logs}

              traces={traces}

              loading={loading || traceLoading}

              refreshing={refreshing || traceRefreshing}

              onRefresh={() => {

                void refreshTrace();

                handleRefresh();

              }}

            />

          ) : activeView === "token" ? (

            <TokenConsoleLayout />

          ) : activeView === "learn" ? (

            <LearnConsoleLayout />

          ) : activeView === "summary" ? (

            <ValueSummaryLayout

              data={data}

              loading={loading}

              refreshing={refreshing}

              error={error}

              isExample={sourceMeta.isExample}

              isEmpty={isEmpty}

            />

          ) : activeView === "workbench" ? (

            <WorkbenchLayout

              data={data}

              loading={loading}

              refreshing={refreshing}

              error={error}

              intentResult={intentResult}

              workbenchOffline={!isDemo && !isLive}
              workbenchDisabledHint={
                isWarming ? bi(navL.workbenchWarming) : bi(navL.workbenchOffline)
              }

              onAnalyze={async () => {

                await synthesize(cseWindow);

                await refreshTrace();

                handleRefresh();

              }}

              onIntentResult={(mode: IntentMode, payload) => {

                if (mode === "analyze") setIntentResult(null);

                else setIntentResult(payload);

                void refresh(cseWindow);

                void refreshTrace();

              }}

              onImported={() => {

                void refresh(cseWindow);

                void refreshTrace();

              }}

            />

          ) : (

            <LearnConsoleLayout />

          )}

        </main>



        <footer className="lg:hidden px-4 py-2 border-t text-center">

          <button type="button" className="text-xs" style={{ color: t.textMuted }} onClick={disconnect}>

            {bi(navL.switchDataSource)}

          </button>

        </footer>

      </div>

    </div>

  );

}


