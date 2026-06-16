import { Suspense } from "react";
import { MindShellPage } from "@/components/mind/MindShellPage";

export default function MindHomePage() {
  return (
    <Suspense fallback={null}>
      <MindShellPage />
    </Suspense>
  );
}
