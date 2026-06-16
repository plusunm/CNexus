"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import type { OverviewView } from "@/cnexus-kernel/shellTypes";

export function useShellNavigation() {
  const router = useRouter();

  const navigateOverviewView = useCallback(
    (view: OverviewView) => {
      const base = "/shell?layout=overview";
      router.push(view === "learn" ? base : `${base}&view=${view}`);
    },
    [router],
  );

  const navigateDebuggerAfterImport = useCallback(() => {
    navigateOverviewView("debugger");
  }, [navigateOverviewView]);

  return { navigateOverviewView, navigateDebuggerAfterImport };
}
