"use client";

import { useSearchParams } from "next/navigation";
import MindShell from "./MindShell";
import { parseShellLayout, parseShellPanel } from "@/cnexus-kernel";

export function MindShellPage() {
  const params = useSearchParams();
  const layout = parseShellLayout(params.get("layout"));
  const panel = parseShellPanel(params.get("panel"));

  return <MindShell layout={layout} panel={panel} />;
}
