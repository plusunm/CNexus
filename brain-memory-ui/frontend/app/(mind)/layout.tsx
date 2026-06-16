import { MindKernelProvider } from "@/cnexus-kernel";

export default function MindLayout({ children }: { children: React.ReactNode }) {
  return <MindKernelProvider>{children}</MindKernelProvider>;
}
