"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import MindShell from "@/components/mind/MindShell";
import type { ShellPanel } from "@/cnexus-kernel/shellTypes";

function parsePanel(value: string | null): ShellPanel | null {
  if (value === "chat" || value === "memory" || value === "upload") return value;
  return null;
}

function DesktopShellInner() {
  const searchParams = useSearchParams();
  const panel = parsePanel(searchParams.get("panel"));
  return <MindShell layout="float" desktop panel={panel} />;
}

export default function DesktopPage() {
  return (
    <Suspense fallback={<MindShell layout="float" desktop />}>
      <DesktopShellInner />
    </Suspense>
  );
}
