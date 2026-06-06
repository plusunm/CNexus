import { create } from "zustand";
import { ModelProfile, RuntimeState, brainApi } from "./api";

type Store = {
  models: ModelProfile[];
  selectedModelId: string;
  runtimeState: RuntimeState | null;
  apiOnline: boolean;
  setModels: (m: ModelProfile[]) => void;
  setSelectedModel: (id: string) => void;
  setRuntimeState: (s: RuntimeState) => void;
  setApiOnline: (v: boolean) => void;
  refreshModels: () => Promise<void>;
  checkHealth: () => Promise<void>;
};

export const useAppStore = create<Store>((set, get) => ({
  models: [],
  selectedModelId: "",
  runtimeState: null,
  apiOnline: false,

  setModels: (models) => set({ models }),
  setSelectedModel: (selectedModelId) => set({ selectedModelId }),
  setRuntimeState: (runtimeState) => set({ runtimeState }),
  setApiOnline: (apiOnline) => set({ apiOnline }),

  refreshModels: async () => {
    const { models } = await brainApi.models();
    set({
      models,
      selectedModelId:
        get().selectedModelId ||
        models.find((m) => m.is_default)?.id ||
        models[0]?.id ||
        "",
    });
  },

  checkHealth: async () => {
    try {
      await brainApi.health();
      set({ apiOnline: true });
    } catch {
      set({ apiOnline: false });
    }
  },
}));
