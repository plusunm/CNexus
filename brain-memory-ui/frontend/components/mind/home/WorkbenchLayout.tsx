"use client";

import type { CognitiveOutput } from "@/lib/cognitiveTypes";
import type { IntentMode } from "@/lib/cognitiveTypes";
import { bi, navL } from "@/lib/spine/labels";
import { IntentTerminal } from "./IntentTerminal";
import { RecommendationPanel } from "./RecommendationPanel";
import { HomeDocumentUpload } from "./HomeDocumentUpload";

type Props = {
  data: CognitiveOutput;
  loading: boolean;
  refreshing?: boolean;
  error: string | null;
  intentResult: string | null;
  workbenchOffline: boolean;
  workbenchDisabledHint?: string;
  onAnalyze: () => Promise<void>;
  onIntentResult: (mode: IntentMode, payload: string) => void;
  onImported: () => void;
};

/** 工作台子页 — 系统对话 · 今日建议 · 上传文件 */
export function WorkbenchLayout({
  data,
  loading,
  refreshing,
  error,
  intentResult,
  workbenchOffline,
  workbenchDisabledHint,
  onAnalyze,
  onIntentResult,
  onImported,
}: Props) {
  return (
    <div className="space-y-5 w-full max-w-[920px]">
      <div className="flex flex-col lg:flex-row gap-4 min-h-[560px] lg:min-h-[640px]">
        <IntentTerminal
          variant="primary"
          intentResult={intentResult}
          disabled={workbenchOffline}
          disabledHint={workbenchDisabledHint ?? bi(navL.workbenchOffline)}
          onAnalyze={onAnalyze}
          onResult={onIntentResult}
        />
        <div className="lg:w-[340px] shrink-0 flex flex-col gap-4 min-h-0">
          <RecommendationPanel data={data} loading={loading} refreshing={refreshing} error={error} />
          <HomeDocumentUpload compact onImported={onImported} />
        </div>
      </div>
    </div>
  );
}
