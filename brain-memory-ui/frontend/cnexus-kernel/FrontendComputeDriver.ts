/**
 * Fast-Path v3 — UI drives predictive compute graph via /v1/system/compute.
 */

import { cnexusProductApi } from "@/lib/api";
import type { useMindStore } from "./MindStore";

type MindStoreApi = ReturnType<typeof useMindStore.getState>;

export type ComputeResult = {
  type?: string;
  status?: string;
  data?: unknown;
  l3?: number;
  cluster?: string;
  intent?: string;
};

export class FrontendComputeDriver {
  private readonly store: () => MindStoreApi;

  constructor(store: () => MindStoreApi) {
    this.store = store;
  }

  async onUserEvent(intent: string, payload: Record<string, unknown> = {}): Promise<ComputeResult> {
    const result = await cnexusProductApi.systemCompute(intent, payload);
    this.render(result);
    return result;
  }

  render(result: ComputeResult): void {
    this.store().applyComputeResult(result);
  }

  async prefetchStatus(): Promise<void> {
    try {
      await this.onUserEvent("status", { source: "bootstrap" });
    } catch {
      /* status prefetch is best-effort */
    }
  }

  async prefetchOverview(): Promise<void> {
    try {
      await this.onUserEvent("overview", { source: "bootstrap" });
    } catch {
      /* overview prefetch is best-effort */
    }
  }
}
