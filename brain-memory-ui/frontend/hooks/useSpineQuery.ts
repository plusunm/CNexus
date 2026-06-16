"use client";

import { useCallback, useState } from "react";
import { querySpineContract } from "@/lib/spine/api";
import type { SpineFrontContractV1, TraceStreamStatus } from "@/lib/spine/contract";

export function useSpineQuery() {
  const [contract, setContract] = useState<SpineFrontContractV1 | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async (query: string, streamStatus: TraceStreamStatus = "REPLAY") => {
    setLoading(true);
    setError(null);
    try {
      const data = await querySpineContract(query, 200, { streamStatus, engine: "v3" });
      setContract(data);
      return data;
    } catch (e) {
      setContract(null);
      const msg = e instanceof Error ? e.message : "spine query failed";
      setError(msg);
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  const patchStreamStatus = useCallback((status: TraceStreamStatus) => {
    setContract((prev) =>
      prev
        ? {
            ...prev,
            trace: { ...prev.trace, status },
            stream: { ...prev.stream, explain_ws: true, live: status === "LIVE" },
          }
        : null,
    );
  }, []);

  return { contract, loading, error, run, patchStreamStatus, setContract };
}
