"use client";

type Props = { data?: { deltas?: { event_id?: string; delta: unknown }[]; patches?: { event_id?: string; delta: unknown }[] } };

export function StateView({ data }: Props) {
  const patches = data?.patches ?? [];
  const deltas = data?.deltas ?? [];

  if (!patches.length && !deltas.length) {
    return <p className="text-sm opacity-70">No state deltas recorded for this trace.</p>;
  }

  return (
    <div className="space-y-3">
      {patches.length ? (
        <div>
          <h4 className="text-xs uppercase tracking-wider opacity-60 mb-2">Tier-A patches</h4>
          <pre className="text-xs overflow-auto max-h-[40vh] p-3 rounded-lg border border-white/10 bg-black/20">
            {JSON.stringify(patches, null, 2)}
          </pre>
        </div>
      ) : null}
      {deltas.length ? (
        <div>
          <h4 className="text-xs uppercase tracking-wider opacity-60 mb-2">All deltas</h4>
          <pre className="text-xs overflow-auto max-h-[40vh] p-3 rounded-lg border border-white/10 bg-black/20">
            {JSON.stringify(deltas, null, 2)}
          </pre>
        </div>
      ) : null}
    </div>
  );
}
