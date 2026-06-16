"use client";

import { Sparkles } from "lucide-react";
import { useMindTheme } from "./MindUiProvider";

type Props = {
  size?: number;
  className?: string;
  rounded?: "lg" | "xl" | "2xl";
  sparkleScale?: number;
  withShadow?: boolean;
};

/** CNexus brand avatar — gradient tile + sparkles (matches app / tray / exe icon). */
export function CnexusAvatarIcon({
  size = 40,
  className = "",
  rounded = "lg",
  sparkleScale = 0.52,
  withShadow = true,
}: Props) {
  const t = useMindTheme();
  const radiusClass = rounded === "2xl" ? "rounded-2xl" : rounded === "xl" ? "rounded-xl" : "rounded-lg";
  const iconSize = Math.max(14, Math.round(size * sparkleScale));

  return (
    <div
      className={`${radiusClass} flex items-center justify-center shrink-0 ${className}`}
      style={{
        width: size,
        height: size,
        background: `linear-gradient(135deg, ${t.blue}, ${t.purple})`,
        ...(withShadow ? { boxShadow: "0 6px 20px rgba(47, 107, 255, 0.35)" } : {}),
      }}
      aria-hidden
    >
      <Sparkles className="text-white" style={{ width: iconSize, height: iconSize }} />
    </div>
  );
}
