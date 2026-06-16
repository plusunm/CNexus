import { DEMO_MIND_OVERVIEW } from "../lib/demoMindOverview";
import { assertMindOverviewContract } from "../cnexus-kernel/MindOverviewContract";

try {
  assertMindOverviewContract(DEMO_MIND_OVERVIEW as unknown as Record<string, unknown>, "DEMO_MIND_OVERVIEW");
  console.log("Demo MindOverview contract: OK");
} catch (err) {
  console.error(String(err));
  process.exit(1);
}
