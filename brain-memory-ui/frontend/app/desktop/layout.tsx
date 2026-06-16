import { MindKernelProvider } from "@/cnexus-kernel";
import { BootShellProtocolRoot } from "@/components/desktop/BootShellProtocolRoot";

export default function DesktopLayout({ children }: { children: React.ReactNode }) {
  return (
    <MindKernelProvider>
      <BootShellProtocolRoot>{children}</BootShellProtocolRoot>
    </MindKernelProvider>
  );
}
