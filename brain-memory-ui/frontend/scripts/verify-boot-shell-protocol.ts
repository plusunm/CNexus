/**
 * BootShell protocol unit checks (no Tauri / no browser required).
 * Run: npm run test:boot-protocol
 */
import assert from "node:assert/strict";
import {
  bootPhaseFromRustState,
  BOOT_STATE_NAMES,
  parseBootHeartbeat,
} from "../lib/bootProtocol";

assert.equal(bootPhaseFromRustState(0), "hydrating");
assert.equal(bootPhaseFromRustState(1), "sync");
assert.equal(bootPhaseFromRustState(3), "float-pending");
assert.equal(bootPhaseFromRustState(4), "float");
assert.equal(
  bootPhaseFromRustState(2, { floatContent: true }),
  "float",
);
assert.equal(
  bootPhaseFromRustState(1, { degraded: true }),
  "degraded",
);

const hb = parseBootHeartbeat({
  phase: "config",
  rustBootState: 0,
  mounted: true,
  ts: 1,
});
assert.ok(hb);
assert.equal(hb!.phase, "config");

assert.equal(parseBootHeartbeat(null), null);
assert.equal(parseBootHeartbeat({ bad: true }), null);

assert.equal(BOOT_STATE_NAMES[4], "FloatWindowShown");

console.log("verify-boot-shell-protocol: OK");
