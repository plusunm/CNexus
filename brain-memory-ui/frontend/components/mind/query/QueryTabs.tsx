"use client";



import clsx from "clsx";

import { useQueryStore } from "@/lib/queryStore";

import type { SpineQueryTab } from "@/lib/spine/contract";

import { useMindTheme } from "../MindUiProvider";



const TABS: { id: SpineQueryTab; label: string }[] = [

  { id: "execution", label: "EXECUTION" },

  { id: "causal", label: "CAUSAL" },

  { id: "state", label: "STATE" },

  { id: "control", label: "CONTROL" },

  { id: "explain", label: "EXPLAIN" },

  { id: "inspector", label: "INSPECTOR" },

];



export function QueryTabs() {

  const t = useMindTheme();

  const { tab, setTab } = useQueryStore();



  return (

    <div className="flex flex-wrap gap-2">

      {TABS.map(({ id, label }) => {

        const active = tab === id;

        return (

          <button

            key={id}

            type="button"

            onClick={() => setTab(id)}

            className={clsx("text-[11px] px-3 py-1.5 rounded-md font-medium tracking-wide transition")}

            style={{

              backgroundColor: active ? t.sidebarActive : t.surface,

              color: active ? "#5eead4" : t.textMuted,

              border: `1px solid ${active ? t.border : "transparent"}`,

            }}

          >

            {label}

          </button>

        );

      })}

    </div>

  );

}

