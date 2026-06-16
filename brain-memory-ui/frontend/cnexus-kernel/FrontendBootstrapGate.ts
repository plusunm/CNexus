/**
 * Fast-Path v2 bootstrap — progressive shell UI, capability SSOT for gates.
 */

import { fastPathV2Enabled, subscribeSystemReadyStream } from "@/lib/api";
import { FrontendRenderer, type StreamReadyEvent } from "./FrontendRenderer";
import type { useMindStore } from "./MindStore";

type MindStoreApi = ReturnType<typeof useMindStore.getState>;

export type FrontendBootstrapGateOptions = {
  store: () => MindStoreApi;
  syncModels?: () => Promise<void>;
};

export class FrontendBootstrapGate {
  private readonly store: () => MindStoreApi;
  private readonly syncModels?: () => Promise<void>;
  private readonly renderer: FrontendRenderer;

  constructor(options: FrontendBootstrapGateOptions) {
    this.store = options.store;
    this.syncModels = options.syncModels;
    this.renderer = new FrontendRenderer(options.store);
  }

  async load(): Promise<"ready" | "warming" | "offline"> {
    if (fastPathV2Enabled()) {
      return this.loadStreaming();
    }
    return this.loadCapabilitySnapshot();
  }

  private phaseFromStore(): "ready" | "warming" | "offline" {
    const s = this.store();
    if (s.runtimeOperationalReady) return "ready";
    if (s.runtimeReachable) return "warming";
    return "offline";
  }

  private async loadStreaming(): Promise<"ready" | "warming" | "offline"> {
    return new Promise((resolve) => {
      let settled = false;
      const finish = (value: "ready" | "warming" | "offline") => {
        if (settled) return;
        settled = true;
        resolve(value);
      };

      const unsubscribe = subscribeSystemReadyStream((event: StreamReadyEvent) => {
        this.renderer.onStream(event);
        if (event.phase === "shell") {
          finish("warming");
        }
        if (event.phase === "final") {
          void this.backgroundHydrate().then(() => finish(this.phaseFromStore()));
        }
      });

      window.setTimeout(() => {
        unsubscribe();
        if (!settled) {
          void this.loadCapabilitySnapshot().then(finish);
        }
      }, 8000);
    });
  }

  private async loadCapabilitySnapshot(): Promise<"ready" | "warming" | "offline"> {
    await this.store().syncSystemCapability();
    void this.backgroundHydrate();
    return this.phaseFromStore();
  }

  backgroundHydrate(): Promise<void> {
    return (async () => {
      try {
        await this.store().syncSystemCapability();
        await this.store().hydrateRuntimeData();
        if (this.syncModels) {
          await this.syncModels();
        }
      } catch {
        /* background hydrate must not regress shell */
      }
    })();
  }
}
