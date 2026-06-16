"use client";

import { useEffect, useMemo, useState, type RefObject } from "react";
import type { FloatStage } from "@/lib/floatingBarStorage";
import {
  FLOAT_MEMORY_PANEL_CHROME,
  computeFloatFactorGraphFrame,
  refineFloatFactorGraphFrame,
  type FloatFactorGraphFrame,
} from "@/lib/floatFactorGraphLayout";

export function useFloatFactorGraphFrame(
  stage: FloatStage,
  panelRef: RefObject<HTMLElement | null>,
): FloatFactorGraphFrame {
  const theoretical = useMemo(() => computeFloatFactorGraphFrame(stage), [stage]);
  const [frame, setFrame] = useState<FloatFactorGraphFrame>(theoretical);

  useEffect(() => {
    setFrame(theoretical);
  }, [theoretical]);

  useEffect(() => {
    const root = panelRef.current;
    if (!root) return;

    const mem = FLOAT_MEMORY_PANEL_CHROME;

    const remeasure = () => {
      const headerEl = root.querySelector<HTMLElement>("[data-cnexus-float-factor-header]");
      const headerH = headerEl?.offsetHeight ?? mem.sectionHeader;

      setFrame(
        refineFloatFactorGraphFrame(
          stage,
          root.clientWidth,
          root.clientHeight,
          headerH,
          theoretical,
        ),
      );
    };

    const ro = new ResizeObserver(remeasure);
    ro.observe(root);
    if (root.parentElement) ro.observe(root.parentElement);
    remeasure();

    const t0 = window.setTimeout(remeasure, 0);
    const t1 = window.setTimeout(remeasure, 120);
    return () => {
      ro.disconnect();
      window.clearTimeout(t0);
      window.clearTimeout(t1);
    };
  }, [stage, theoretical, panelRef]);

  return frame;
}
