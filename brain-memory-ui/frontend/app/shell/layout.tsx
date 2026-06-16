"use client";

import { MindKernelProvider } from "@/cnexus-kernel";

export default function ShellLayout({ children }: { children: React.ReactNode }) {
  return <MindKernelProvider>{children}</MindKernelProvider>;
}
