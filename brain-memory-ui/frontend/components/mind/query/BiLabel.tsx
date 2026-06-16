"use client";

import type { BilingualLabel } from "@/lib/spine/labels";
import { projectBiSection } from "@/lib/spine/labels";
import { useLanguageProjection } from "../LanguageProjectionSwitch";

type Props = {
  label: BilingualLabel;
  className?: string;
  style?: React.CSSProperties;
  as?: "h2" | "h3" | "span" | "p";
};

/** Section title — SIBT projection mode (zh / en / both). */
export function BiLabel({ label, className = "", style, as: Tag = "h3" }: Props) {
  const projection = useLanguageProjection();
  return (
    <Tag className={className} style={style}>
      {projectBiSection(label, projection)}
    </Tag>
  );
}

/** Inline muted caption with projection mode. */
export function BiCaption({ label, className = "", style }: Omit<Props, "as">) {
  const projection = useLanguageProjection();
  return (
    <span className={className} style={style}>
      {projectBiSection(label, projection)}
    </span>
  );
}
