"use client";

export { MindConnectionProvider as KernelMindConnectionProvider } from "@/cnexus-kernel";
import {
  MindConnectionProvider as KernelProvider,
  useMindConnection as useKernelMindConnection,
} from "@/cnexus-kernel";

export function MindConnectionProvider({ children }: { children: React.ReactNode }) {
  return <KernelProvider>{children}</KernelProvider>;
}

/** UI compat — maps preference ↔ legacy mode naming. */
export function useMindConnection() {
  const ctx = useKernelMindConnection();
  return {
    ...ctx,
    mode: ctx.preference,
    selectMode: ctx.selectPreference,
  };
}
