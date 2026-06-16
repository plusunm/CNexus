import { spineQuery } from "@/lib/spineQueryApi";
import type { SpineQueryResponse } from "@/lib/spineQueryTypes";
import { mapToSpineFrontContract } from "./mapContract";
import type { SpineFrontContractV1, TraceStreamStatus } from "./contract";

export async function querySpineContract(
  query: string,
  limit = 200,
  opts?: { streamStatus?: TraceStreamStatus; engine?: "v1" | "v2" | "v3" },
): Promise<SpineFrontContractV1> {
  const started = performance.now();
  const raw: SpineQueryResponse = await spineQuery(query, limit, { engine: opts?.engine ?? "v3" });
  return mapToSpineFrontContract(raw, {
    streamStatus: opts?.streamStatus ?? "REPLAY",
    latencyMs: Math.round(performance.now() - started),
  });
}

export async function querySpineByTraceId(
  traceId: string,
  mode = "explain",
  limit = 200,
  opts?: { streamStatus?: TraceStreamStatus },
): Promise<SpineFrontContractV1> {
  const q = `TRACE ${traceId.trim()} EXPLAIN ${mode}`;
  return querySpineContract(q, limit, opts);
}
