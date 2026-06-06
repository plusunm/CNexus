"use client";

import { useEffect } from "react";
import { Sidebar } from "@/components/Sidebar";
import { useAppStore } from "@/lib/store";
import { brainApi } from "@/lib/api";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { apiOnline, checkHealth, refreshModels, setRuntimeState } = useAppStore();

  useEffect(() => {
    checkHealth();
    refreshModels();
    const ws = brainApi.connectStateStream(setRuntimeState);
    return () => ws.close();
  }, [checkHealth, refreshModels, setRuntimeState]);

  return (
    <div className="flex min-h-screen bg-bg text-gray-100">
      <Sidebar apiOnline={apiOnline} />
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}
