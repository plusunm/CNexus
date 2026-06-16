"use client";

import { ChatPanel } from "../ChatPanel";
import { FloatingMemoryPanel } from "./FloatingMemoryPanel";
import { FloatingUploadPanel } from "./FloatingUploadPanel";
import { useFloatingBarStore } from "@/lib/floatingBarStore";
import { FloatingCognitiveHints } from "./FloatingCognitiveHints";
import type { FloatPanel } from "@/lib/floatingBarStorage";

type Props = {
  panel: FloatPanel;
};

export function FloatingExpandPanel({ panel }: Props) {
  const sessionEpoch = useFloatingBarStore((s) => s.sessionEpoch);

  return (
    <div className="min-h-0 flex flex-col min-w-0 overflow-hidden flex-1" data-no-drag>
      <FloatingCognitiveHints />
      <div
        key={`${sessionEpoch}-${panel}`}
        className="px-3 pb-3 pt-0 min-h-0 flex flex-col min-w-0 overflow-hidden flex-1"
      >
        <div className="min-h-0 min-w-0 flex flex-col overflow-hidden h-full">
          {panel === "chat" && <ChatPanel variant="float" autoFocusInput />}
          {panel === "memory" && <FloatingMemoryPanel />}
          {panel === "upload" && <FloatingUploadPanel />}
        </div>
      </div>
    </div>
  );
}
