"use client";

import clsx from "clsx";
import { bi, tokenL } from "@/lib/spine/labels";
import type { TokenTab } from "@/lib/token/types";
import { useTokenStore } from "@/lib/token/tokenStore";
import { useMindTheme } from "../MindUiProvider";

const TABS: { id: TokenTab; labelKey: keyof typeof tokenL }[] = [
  { id: "overview", labelKey: "tabOverview" },
  { id: "events", labelKey: "tabEvents" },
  { id: "field", labelKey: "tabField" },
  { id: "binding", labelKey: "tabBinding" },
  { id: "influence", labelKey: "tabInfluence" },
  { id: "identity", labelKey: "tabIdentity" },
];

export function TokenTabs() {
  const t = useMindTheme();
  const { tab, setTab } = useTokenStore();

  return (
    <div className="flex flex-wrap gap-1.5">
      {TABS.map(({ id, labelKey }) => {
        const active = tab === id;
        return (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={clsx(
              "text-[10px] uppercase tracking-wider px-3 py-1.5 rounded border font-medium transition",
              active ? "opacity-100" : "opacity-60 hover:opacity-80",
            )}
            style={{
              borderColor: active ? t.blue : t.border,
              backgroundColor: active ? t.blueSoft : t.chatBg,
              color: active ? t.blue : t.textMuted,
            }}
          >
            {bi(tokenL[labelKey])}
          </button>
        );
      })}
    </div>
  );
}
