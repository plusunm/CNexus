"use client";



import type { ControlDecisionView } from "@/lib/spine/contract";

import { useMindTheme } from "../../MindUiProvider";



type Props = {

  decisions: ControlDecisionView[];

};



export function ControlView({ decisions }: Props) {

  const t = useMindTheme();



  if (!decisions.length) {

    return <p className="text-sm opacity-70">No control decisions in spine for this trace.</p>;

  }



  return (

    <div className="space-y-2 max-h-[65vh] overflow-auto">

      {decisions.map((d) => (

        <div

          key={d.event_id}

          className="rounded-lg border px-3 py-2 text-xs font-mono"

          style={{ borderColor: t.border, backgroundColor: t.chatBg }}

        >

          <span

            style={{

              color:

                d.decision === "REJECT"

                  ? t.red

                  : d.decision === "WARN"

                    ? t.orange

                    : t.green,

            }}

          >

            {d.decision}

          </span>

          <span className="opacity-70 ml-2">{d.entry ?? d.rule ?? "—"}</span>

          {d.caller ? <span className="opacity-50 ml-2">caller={d.caller}</span> : null}

        </div>

      ))}

    </div>

  );

}

