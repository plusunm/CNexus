import { MindKernelProvider } from "@/cnexus-kernel";

export default function PlatformLayout({ children }: { children: React.ReactNode }) {
  return (
    <MindKernelProvider>
      <div className="min-h-screen bg-bg text-gray-100">{children}</div>
    </MindKernelProvider>
  );
}
