"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { initCnexusConfig } from "@/lib/cnexusConfig";
import { startSecurityHeartbeat, stopSecurityHeartbeat } from "@/lib/securityBootstrap";
import { isTauriDesktop } from "@/lib/tauriDesktop";
import {
  defaultConnectionPreference,
  getEdition,
  getEditionProfile,
} from "./edition";
import {
  clearConnectionPreference,
  loadConnectionPreference,
  resolveEffectiveMode,
  saveConnectionPreference,
  type ConnectionPreference,
  type EffectiveConnectionMode,
} from "./connectionMode";
import { useMindStore } from "./MindStore";

type MindConnectionContextValue = {
  preference: ConnectionPreference | null;
  effectiveMode: EffectiveConnectionMode;
  runtimeEnabled: boolean;
  configReady: boolean;
  selectPreference: (mode: ConnectionPreference) => void;
  disconnect: () => void;
  hydrated: boolean;
};

const MindConnectionContext = createContext<MindConnectionContextValue | null>(null);

export function MindConnectionProvider({ children }: { children: React.ReactNode }) {
  const [preference, setPreference] = useState<ConnectionPreference | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [configReady, setConfigReady] = useState(false);
  const runtimeReachable = useMindStore((s) => s.runtimeReachable);
  const resetRuntimeBinding = useMindStore((s) => s.resetRuntimeBinding);
  const setEffectiveMode = useMindStore((s) => s.setEffectiveMode);

  const effectiveMode = useMemo(
    () =>
      resolveEffectiveMode(preference, runtimeReachable, {
        tauriDesktop: isTauriDesktop(),
      }),
    [preference, runtimeReachable],
  );

  useEffect(() => {
    setEffectiveMode(effectiveMode);
  }, [effectiveMode, setEffectiveMode]);

  useEffect(() => {
    initCnexusConfig().finally(() => {
      const profile = getEditionProfile(getEdition());
      let pref = loadConnectionPreference();

      if (profile.requireRuntime) {
        pref = "runtime";
        saveConnectionPreference("runtime");
      } else if (pref === null) {
        const fallback = defaultConnectionPreference(getEdition(), {
          tauriDesktop: isTauriDesktop(),
        });
        if (fallback) {
          pref = fallback;
          saveConnectionPreference(fallback);
        }
      }

      if (!profile.allowDemo && pref === "demo") {
        pref = "runtime";
        saveConnectionPreference("runtime");
      }

      setPreference(pref);
      setConfigReady(true);
      setHydrated(true);
    });
  }, []);

  useEffect(() => {
    if (!hydrated || !configReady) return;
    if (!isTauriDesktop()) return;
    const profile = getEditionProfile(getEdition());
    if (!profile.licenseRequired) return;

    startSecurityHeartbeat();
    return () => stopSecurityHeartbeat();
  }, [hydrated, configReady]);

  const selectPreference = useCallback(
    (next: ConnectionPreference) => {
      const profile = getEditionProfile(getEdition());
      if (next === "demo" && !profile.allowDemo) return;
      if (next === "runtime" && !profile.allowRuntimeConnect) return;
      if (next === "demo") resetRuntimeBinding();
      setPreference(next);
      saveConnectionPreference(next);
    },
    [resetRuntimeBinding],
  );

  const disconnect = useCallback(() => {
    resetRuntimeBinding();
    setPreference(null);
    clearConnectionPreference();
  }, [resetRuntimeBinding]);

  const pendingValue = useMemo(
    (): MindConnectionContextValue => ({
      preference: null,
      effectiveMode: "demo",
      runtimeEnabled: false,
      configReady: false,
      selectPreference: () => {},
      disconnect: () => {},
      hydrated: false,
    }),
    [],
  );

  const value = useMemo(
    (): MindConnectionContextValue => ({
      preference,
      effectiveMode,
      runtimeEnabled: preference === "runtime",
      configReady,
      selectPreference,
      disconnect,
      hydrated,
    }),
    [preference, effectiveMode, configReady, selectPreference, disconnect, hydrated],
  );

  return (
    <MindConnectionContext.Provider value={hydrated && configReady ? value : pendingValue}>
      {children}
    </MindConnectionContext.Provider>
  );
}

export function useMindConnection() {
  const ctx = useContext(MindConnectionContext);
  if (!ctx) throw new Error("useMindConnection must be used within MindConnectionProvider");
  return ctx;
}

/** @deprecated use preference / selectPreference */
export function useMindConnectionLegacy() {
  const ctx = useMindConnection();
  return {
    mode: ctx.preference,
    selectMode: ctx.selectPreference,
    runtimeEnabled: ctx.runtimeEnabled,
    configReady: ctx.configReady,
    disconnect: ctx.disconnect,
    hydrated: ctx.hydrated,
  };
}
