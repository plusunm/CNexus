import { create } from "zustand";

import type { ExecutionRecord } from "@/lib/kernelRecord";
import type { SpineFrontContractV1, SpineQueryTab } from "@/lib/spine/contract";



type QueryStore = {

  query: string;

  setQuery: (q: string) => void;

  loading: boolean;

  setLoading: (v: boolean) => void;

  error: string | null;

  setError: (e: string | null) => void;

  contract: SpineFrontContractV1 | null;

  setContract: (c: SpineFrontContractV1 | null) => void;

  kernelRecord: ExecutionRecord | null;

  setKernelRecord: (r: ExecutionRecord | null) => void;

  tab: SpineQueryTab;

  setTab: (t: SpineQueryTab) => void;

  selectedEventId: string | null;

  setSelectedEventId: (id: string | null) => void;

  stateStepIndex: number;

  setStateStepIndex: (i: number) => void;

};



export const useQueryStore = create<QueryStore>((set) => ({

  query: "",

  setQuery: (q) => set({ query: q }),

  loading: false,

  setLoading: (v) => set({ loading: v }),

  error: null,

  setError: (e) => set({ error: e }),

  contract: null,

  setContract: (c) => set({ contract: c, selectedEventId: null, stateStepIndex: 0 }),

  kernelRecord: null,

  setKernelRecord: (r) => set({ kernelRecord: r }),

  tab: "execution",

  setTab: (t) => set({ tab: t }),

  selectedEventId: null,

  setSelectedEventId: (id) => set({ selectedEventId: id }),

  stateStepIndex: 0,

  setStateStepIndex: (i) => set({ stateStepIndex: i }),

}));

