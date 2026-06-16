"use client";

import { Search } from "lucide-react";
import { querySpineContract } from "@/lib/spine/api";
import { fetchExecutionRecord } from "@/lib/kernelRecord";
import { debugSpineEnabled, projectionLockEnabled } from "@/lib/projectionLock";
import { useQueryStore } from "@/lib/queryStore";
import { bi, spineL } from "@/lib/spine/labels";
import { useMindTheme } from "../MindUiProvider";

type Props = {
  disabled?: boolean;
  disabledHint?: string;
  streamLive?: boolean;
};

export function QueryBar({ disabled, disabledHint, streamLive }: Props) {
  const t = useMindTheme();
  const { query, setQuery, setLoading, setContract, setKernelRecord, setError } = useQueryStore();

  const run = async () => {
    if (disabled) return;
    setLoading(true);
    setError(null);
    try {
      const traceId = query.trim();
      if (projectionLockEnabled() && !debugSpineEnabled()) {
        const record = await fetchExecutionRecord(traceId);
        setKernelRecord(record);
        setContract(null);
        return;
      }
      setKernelRecord(null);
      const contract = await querySpineContract(query, 200, {
        streamStatus: streamLive ? "LIVE" : "REPLAY",
      });
      setContract(contract);
    } catch (e) {
      setContract(null);
      setKernelRecord(null);
      setError(e instanceof Error ? e.message : bi(spineL.queryFailed));
    } finally {
      setLoading(false);
    }
  };

  const hint = disabledHint ?? bi(spineL.runtimeRequired);

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void run();
          }}
          disabled={disabled}
          placeholder={bi(spineL.queryPlaceholder)}
          className="flex-1 text-sm px-3 py-2 rounded-lg border outline-none font-mono"
          style={{
            borderColor: t.border,
            backgroundColor: t.chatBg,
            color: t.text,
          }}
        />
        <button
          type="button"
          onClick={() => void run()}
          disabled={disabled}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50"
          style={{ backgroundColor: t.blue, color: "#fff" }}
        >
          <Search className="w-4 h-4" />
          {bi(spineL.query)}
        </button>
      </div>
      {disabled ? (
        <p className="text-xs" style={{ color: t.orange }}>
          {hint}
        </p>
      ) : null}
    </div>
  );
}
