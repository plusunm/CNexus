"use client";

import { Suspense, useEffect } from "react";
import { useRouter } from "next/navigation";
import { MindShellPage } from "@/components/mind/MindShellPage";
import { isTauriDesktop, listenDashboardNavigate } from "@/lib/tauriDesktop";

function ShellRouteNavigator() {
  const router = useRouter();

  useEffect(() => {
    if (!isTauriDesktop()) return;
    let unlisten: (() => void) | undefined;
    void listenDashboardNavigate((path) => {
      router.replace(path);
    }).then((fn) => {
      unlisten = fn;
    });
    return () => unlisten?.();
  }, [router]);

  return null;
}

export default function ShellRoutePage() {
  return (
    <Suspense fallback={null}>
      <ShellRouteNavigator />
      <MindShellPage />
    </Suspense>
  );
}
