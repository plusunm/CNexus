"use client";



import type { SpineFrontContractV1 } from "@/lib/spine/contract";



type Props = {

  explanation: SpineFrontContractV1["explanation"];

};



function StoryBlock({ title, lines }: { title: string; lines?: string[] }) {

  if (!lines?.length) return null;

  return (

    <div>

      <h4 className="text-xs uppercase tracking-wider opacity-60 mb-2">{title}</h4>

      <ul className="text-xs space-y-1 font-mono opacity-90">

        {lines.map((line) => (

          <li key={line}>{line}</li>

        ))}

      </ul>

    </div>

  );

}



export function ExplainView({ explanation }: Props) {

  if (!explanation.narrative && !explanation.root_causes.length) {

    return <p className="text-sm opacity-70">Run a query to generate explanation.</p>;

  }



  return (

    <div className="space-y-4 max-w-3xl">

      {explanation.root_causes.length ? (

        <div>

          <h3 className="text-sm font-semibold mb-2">Root Cause</h3>

          <ul className="text-xs font-mono space-y-1 opacity-90">

            {explanation.root_causes.map((r) => (

              <li key={r}>· {r}</li>

            ))}

          </ul>

        </div>

      ) : null}



      <div>

        <h3 className="text-sm font-semibold mb-2">Narrative</h3>

        <p className="text-sm leading-relaxed whitespace-pre-wrap">{explanation.narrative || "—"}</p>

      </div>



      <StoryBlock title="Execution path" lines={explanation.execution_path_labels} />
      {explanation.execution_narrative ? (
        <div>
          <h3 className="text-sm font-semibold mb-2">Execution narrative</h3>
          <p className="text-xs font-mono opacity-90">{explanation.execution_narrative}</p>
        </div>
      ) : null}

      <StoryBlock title="Causal story" lines={explanation.causal_story} />

      <StoryBlock title="State story" lines={explanation.state_story} />

      <StoryBlock title="Control story" lines={explanation.control_story} />

    </div>

  );

}

