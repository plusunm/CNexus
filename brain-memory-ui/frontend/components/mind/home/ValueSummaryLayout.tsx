"use client";

import type { CognitiveOutput } from "@/lib/cognitiveTypes";
import { ValueSummaryPanel } from "./ValueSummaryPanel";
import { PersonalityObservationPanel } from "./PersonalityObservationPanel";
import { IntentObservationPanel } from "./IntentObservationPanel";
import { StatusCardsRow } from "../StatusCardsRow";

type Props = {
  data: CognitiveOutput;
  loading: boolean;
  refreshing?: boolean;
  error: string | null;
  isExample: boolean;
  isEmpty: boolean;
};

/** 运行摘要子页 — CSE 叙事 + 人格/意向观测 */
export function ValueSummaryLayout({ data, loading, refreshing, error, isExample, isEmpty }: Props) {
  return (
    <div className="space-y-5 w-full max-w-[920px]">
      <ValueSummaryPanel
        data={data}
        loading={loading}
        refreshing={refreshing}
        error={error}
        isExample={isExample}
        isEmpty={isEmpty}
      />
      <StatusCardsRow />
      <PersonalityObservationPanel />
      <IntentObservationPanel />
    </div>
  );
}
