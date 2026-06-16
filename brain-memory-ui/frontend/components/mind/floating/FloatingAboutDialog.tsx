"use client";

import { ExternalLink } from "lucide-react";
import { CNEXUS_ABOUT } from "@/lib/cnexusAbout";
import { floatTy } from "@/lib/floatTypography";
import { useMindTheme } from "../MindUiProvider";
import { FloatingMiniDialog } from "./FloatingMiniDialog";

type Props = {
  onClose: () => void;
};

export function FloatingAboutDialog({ onClose }: Props) {
  const t = useMindTheme();

  return (
    <FloatingMiniDialog title="关于我们" onClose={onClose} width={300}>
      <div className={`space-y-4 ${floatTy.body}`}>
        <div className="flex items-baseline justify-between gap-3">
          <span style={{ color: t.textMuted }}>版本</span>
          <span className={floatTy.mono} style={{ color: t.text }}>
            {CNEXUS_ABOUT.version}
          </span>
        </div>

        <div className="space-y-1.5">
          <span className="block" style={{ color: t.textMuted }}>
            联系方式
          </span>
          <a
            href={CNEXUS_ABOUT.contactUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 p-2 rounded-lg transition hover:brightness-110 break-all"
            style={{
              backgroundColor: "rgba(255,255,255,0.04)",
              border: `1px solid ${t.border}`,
              color: t.blue,
            }}
          >
            <ExternalLink className="w-3.5 h-3.5 shrink-0" />
            {CNEXUS_ABOUT.contactUrl}
          </a>
        </div>
      </div>
    </FloatingMiniDialog>
  );
}
