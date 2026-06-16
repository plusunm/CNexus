"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchTokenField } from "@/lib/token/api";
import type { TokenField } from "@/lib/token/types";

export function useTokenField(traceId: string | null) {
  const [tokenField, setTokenField] = useState<TokenField | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!traceId) {
      setTokenField(null);
      return null;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await fetchTokenField(traceId);
      setTokenField(data);
      return data;
    } catch (e) {
      setTokenField(null);
      const msg = e instanceof Error ? e.message : "token field load failed";
      setError(msg);
      return null;
    } finally {
      setLoading(false);
    }
  }, [traceId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { tokenField, loading, error, refresh };
}
