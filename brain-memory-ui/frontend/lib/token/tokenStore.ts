import { create } from "zustand";
import type { TokenField, TokenTab, TokenTrace } from "./types";

type TokenStore = {
  traceInput: string;
  setTraceInput: (v: string) => void;
  selectedTraceId: string | null;
  setSelectedTraceId: (id: string | null) => void;
  traces: TokenTrace[];
  setTraces: (t: TokenTrace[]) => void;
  report: TokenField | null;
  setReport: (r: TokenField | null) => void;
  loading: boolean;
  setLoading: (v: boolean) => void;
  reportLoading: boolean;
  setReportLoading: (v: boolean) => void;
  error: string | null;
  setError: (e: string | null) => void;
  tab: TokenTab;
  setTab: (t: TokenTab) => void;
  selectedEventId: string | null;
  setSelectedEventId: (id: string | null) => void;
};

export const useTokenStore = create<TokenStore>((set) => ({
  traceInput: "",
  setTraceInput: (traceInput) => set({ traceInput }),
  selectedTraceId: null,
  setSelectedTraceId: (selectedTraceId) => set({ selectedTraceId }),
  traces: [],
  setTraces: (traces) => set({ traces }),
  report: null,
  setReport: (report) => set({ report }),
  loading: false,
  setLoading: (loading) => set({ loading }),
  reportLoading: false,
  setReportLoading: (reportLoading) => set({ reportLoading }),
  error: null,
  setError: (error) => set({ error }),
  tab: "overview",
  setTab: (tab) => set({ tab }),
  selectedEventId: null,
  setSelectedEventId: (selectedEventId) => set({ selectedEventId }),
}));
