/**
 * Fast-Path v2 — progressive UI renderer driven by streaming ready phases.
 */

import type { useMindStore } from "./MindStore";

export type StreamReadyPhase = "shell" | "local" | "cluster" | "final";

export type StreamReadyEvent = {
  phase: StreamReadyPhase;
  status?: string;
  render_mode?: string;
  boot_phase?: string;
  ws?: string;
  l3?: boolean;
  memory?: string;
  cluster?: string;
  consensus?: string;
  crdt?: string;
  ready?: boolean;
  gate?: Record<string, unknown>;
};

type MindStoreApi = ReturnType<typeof useMindStore.getState>;

export class FrontendRenderer {
  private readonly store: () => MindStoreApi;
  private state: Record<string, unknown> = {};

  constructor(store: () => MindStoreApi) {
    this.store = store;
  }

  onStream(event: StreamReadyEvent): void {
    this.state = { ...this.state, ...event };
    const phase = event.phase;

    if (phase === "shell") {
      this.renderShell(event);
    } else if (phase === "local") {
      this.updateLocalState(event);
    } else if (phase === "cluster") {
      this.showClusterPending(event);
    } else if (phase === "final") {
      this.markReady(event);
    }

    this.store().applyStreamEvent(event);
  }

  renderShell(event: StreamReadyEvent): void {
    this.store().applyFastReadySnapshot({
      status: event.status ?? "rendering_ui",
      boot_phase: event.boot_phase,
      ws: event.ws,
      render_mode: event.render_mode ?? "fast_path_v2",
    });
  }

  updateLocalState(event: StreamReadyEvent): void {
    this.store().setRuntimeReachable(true);
  }

  showClusterPending(_event: StreamReadyEvent): void {
    /* cluster warming is non-blocking — shell stays interactive */
  }

  markReady(event: StreamReadyEvent): void {
    if (event.ready || event.status === "ready") {
      this.store().setRuntimeReachable(true);
    }
  }
}
