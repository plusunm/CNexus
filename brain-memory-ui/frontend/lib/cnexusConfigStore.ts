"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { CNexusConfig, ConfigPresetId } from "./cognitiveTypes";
import { CONFIG_PRESETS } from "./cognitiveTypes";

const DEFAULT_CONFIG: CNexusConfig = {
  system: { mode: "local", debug_trace: true },
  model: {
    llm_provider: "ollama",
    chat_model: "llama3.2",
    embedding_model: "nomic-embed-text",
  },
  scheduler: { max_concurrency: 1, embed_chat_mutex: true },
  cse: { enabled: true, window_size: 120, auto_synthesize: true },
  governance: { strict_mode: true, allow_runtime_mutation: false },
};

function deepMerge<T extends Record<string, unknown>>(base: T, patch: Partial<T>): T {
  const out = { ...base };
  for (const key of Object.keys(patch) as (keyof T)[]) {
    const val = patch[key];
    if (val && typeof val === "object" && !Array.isArray(val)) {
      out[key] = deepMerge(
        (base[key] as Record<string, unknown>) || {},
        val as Record<string, unknown>,
      ) as T[keyof T];
    } else if (val !== undefined) {
      out[key] = val as T[keyof T];
    }
  }
  return out;
}

/** Governance gatekeeper — config cannot break Scheduler invariants. */
export function validateConfig(config: CNexusConfig): CNexusConfig {
  const validated = structuredClone(config);
  if (validated.scheduler.max_concurrency > 2) {
    validated.scheduler.max_concurrency = 2;
  }
  if (validated.scheduler.embed_chat_mutex) {
    validated.scheduler.max_concurrency = 1;
  }
  if (validated.governance.strict_mode && validated.governance.allow_runtime_mutation) {
    validated.governance.allow_runtime_mutation = false;
  }
  validated.cse.window_size = Math.min(500, Math.max(20, validated.cse.window_size));
  return validated;
}

type ConfigState = {
  config: CNexusConfig;
  activePreset: ConfigPresetId | null;
  lastActionApplied: string | null;
  updateConfig: (patch: Partial<CNexusConfig>) => void;
  applyPreset: (id: ConfigPresetId) => void;
  resetToDefault: () => void;
  setLastAction: (action: string | null) => void;
};

export const useCnexusConfigStore = create<ConfigState>()(
  persist(
    (set, get) => ({
      config: DEFAULT_CONFIG,
      activePreset: "safe",
      lastActionApplied: null,
      updateConfig: (patch) =>
        set((state) => ({
          config: validateConfig(deepMerge(state.config, patch)),
          activePreset: null,
        })),
      applyPreset: (id) => {
        const preset = CONFIG_PRESETS[id];
        set((state) => ({
          config: validateConfig(deepMerge(state.config, preset.patch)),
          activePreset: id,
        }));
      },
      resetToDefault: () => set({ config: DEFAULT_CONFIG, activePreset: null }),
      setLastAction: (action) => set({ lastActionApplied: action }),
    }),
    { name: "cnexus-config-v1" },
  ),
);

export function getConfigSnapshot(): CNexusConfig {
  return useCnexusConfigStore.getState().config;
}
