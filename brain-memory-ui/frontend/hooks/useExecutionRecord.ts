"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchExecutionRecord, type ExecutionRecord } from "@/lib/kernelRecord";

type State = {
  record: ExecutionRecord | null;
  loading: boolean;
  error: string | null;
};

export function useExecutionRecord(traceId: string | null, enabled = true) {
  const [state, setState] = useState<State>({
    record: null,
    loading: false,
    error: null,
  });

  const refresh = useCallback(async () => {
    if (!traceId || !enabled) {
      setState({ record: null, loading: false, error: null });
      return;
    }
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const record = await fetchExecutionRecord(traceId);
      setState({ record, loading: false, error: null });
    } catch (e) {
      setState({
        record: null,
        loading: false,
        error: e instanceof Error ? e.message : "execution record fetch failed",
      });
    }
  }, [traceId, enabled]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { ...state, refresh };
}
