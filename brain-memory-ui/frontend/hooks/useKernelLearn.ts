"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchKernelLearn, type LearnExplanationV2 } from "@/lib/kernelRecord";

export function useKernelLearn(traceId: string | null) {
  const [learn, setLearn] = useState<LearnExplanationV2 | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (overrideId?: string) => {
    const id = (overrideId || traceId || "").trim();
    if (!id) {
      setLearn(null);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await fetchKernelLearn(id);
      setLearn(data);
    } catch (e) {
      setLearn(null);
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [traceId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { learn, loading, error, refresh };
}
