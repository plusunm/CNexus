"use client";

type Props = { data?: Record<string, unknown>[] };

export function EventView({ data }: Props) {
  if (!data?.length) {
    return <p className="text-sm opacity-70">No events.</p>;
  }
  return (
    <pre className="text-xs overflow-auto max-h-[70vh] p-3 rounded-lg border border-white/10 bg-black/20">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}
