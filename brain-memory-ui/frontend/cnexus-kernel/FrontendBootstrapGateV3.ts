/**
 * Fast-Path v3 bootstrap — instant UI shell, capability SSOT for gates.
 */

import { fastPathV3Enabled } from "@/lib/api";
import { FrontendBootstrapGate, type FrontendBootstrapGateOptions } from "./FrontendBootstrapGate";
import { FrontendComputeDriver } from "./FrontendComputeDriver";

export class FrontendBootstrapGateV3 {
  private readonly fallback: FrontendBootstrapGate;
  private readonly compute: FrontendComputeDriver;
  private readonly store: FrontendBootstrapGateOptions["store"];

  constructor(options: FrontendBootstrapGateOptions) {
    this.store = options.store;
    this.fallback = new FrontendBootstrapGate(options);
    this.compute = new FrontendComputeDriver(options.store);
  }

  async load(): Promise<"ready" | "warming" | "offline"> {
    try {
      await this.store().syncSystemCapability();
      void this.backgroundCompute();
      const s = this.store();
      if (s.runtimeOperationalReady) return "ready";
      if (s.runtimeReachable) return "warming";
      return "offline";
    } catch {
      return this.fallback.load();
    }
  }

  backgroundCompute(): void {
    void (async () => {
      await this.compute.prefetchStatus();
      await this.store().syncSystemCapability();
      await this.store().hydrateRuntimeData();
      await this.compute.prefetchOverview();
    })();
  }

  getComputeDriver(): FrontendComputeDriver {
    return this.compute;
  }
}

export type BootstrapGate = FrontendBootstrapGate | FrontendBootstrapGateV3;

/** Factory — v3 when enabled, else v2/v1 gate. */
export function createBootstrapGate(options: FrontendBootstrapGateOptions): BootstrapGate {
  if (fastPathV3Enabled()) {
    return new FrontendBootstrapGateV3(options);
  }
  return new FrontendBootstrapGate(options);
}
