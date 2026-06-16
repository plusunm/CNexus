"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { cognitiveTheme } from "./themes/cognitiveTheme";
import { floatTheme } from "./themes/floatTheme";
import { overviewTheme } from "./themes/overviewTheme";
import {
  loadMindUiMode,
  saveMindUiMode,
  type MindTheme,
  type MindUiMode,
} from "./themes/types";

type MindUiContextValue = {
  mode: MindUiMode;
  theme: MindTheme;
  setMode: (mode: MindUiMode) => void;
  toggleMode: () => void;
};

const MindUiContext = createContext<MindUiContextValue | null>(null);

export function MindUiProvider({ children }: { children: React.ReactNode }) {
  const [mode, setModeState] = useState<MindUiMode>("overview");

  useEffect(() => {
    setModeState(loadMindUiMode());
  }, []);

  const setMode = useCallback((next: MindUiMode) => {
    setModeState(next);
    saveMindUiMode(next);
  }, []);

  const toggleMode = useCallback(() => {
    setModeState((prev) => {
      const next: MindUiMode =
        prev === "overview" ? "cognitive" : prev === "cognitive" ? "float" : "overview";
      saveMindUiMode(next);
      return next;
    });
  }, []);

  const theme =
    mode === "cognitive" ? cognitiveTheme : mode === "float" ? floatTheme : overviewTheme;

  const value = useMemo(
    () => ({ mode, theme, setMode, toggleMode }),
    [mode, theme, setMode, toggleMode],
  );

  return <MindUiContext.Provider value={value}>{children}</MindUiContext.Provider>;
}

export function useMindUi() {
  const ctx = useContext(MindUiContext);
  if (!ctx) throw new Error("useMindUi must be used within MindUiProvider");
  return ctx;
}

export function useMindTheme(): MindTheme {
  return useMindUi().theme;
}

export type { MindTheme, MindUiMode } from "./themes/types";
