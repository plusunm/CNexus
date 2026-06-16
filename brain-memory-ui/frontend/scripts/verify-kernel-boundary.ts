import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(__dirname, "..");

const SCAN_DIRS = ["app", "components", "hooks", "lib"];
const KERNEL_DIR = path.join(ROOT, "cnexus-kernel");
const ALLOWED_LIB = new Set([
  path.normalize(path.join(ROOT, "lib/store.ts")),
  path.normalize(path.join(ROOT, "lib/connectionMode.ts")),
  path.normalize(path.join(ROOT, "lib/mindOverviewContract.ts")),
  path.normalize(path.join(ROOT, "lib/mindOverview.ts")),
  path.normalize(path.join(ROOT, "lib/demoMindOverview.ts")),
  path.normalize(path.join(ROOT, "lib/api.ts")),
  path.normalize(path.join(ROOT, "lib/cnexusConfig.ts")),
  path.normalize(path.join(ROOT, "lib/floatingBarStore.ts")),
  path.normalize(path.join(ROOT, "lib/floatingBarStorage.ts")),
  path.normalize(path.join(ROOT, "lib/runtimeTypes.ts")),
  path.normalize(path.join(ROOT, "lib/tauriDesktop.ts")),
]);

const errors: string[] = [];

function walk(dir: string, out: string[] = []): string[] {
  if (!fs.existsSync(dir)) return out;
  for (const name of fs.readdirSync(dir)) {
    const full = path.join(dir, name);
    const stat = fs.statSync(full);
    if (stat.isDirectory()) {
      if (name === "node_modules" || name === ".next") continue;
      walk(full, out);
    } else if (/\.(tsx?|jsx?)$/.test(name)) {
      out.push(full);
    }
  }
  return out;
}

function isUnderKernel(file: string): boolean {
  return file.startsWith(KERNEL_DIR + path.sep);
}

function rel(file: string): string {
  return path.relative(ROOT, file).replace(/\\/g, "/");
}

function checkFile(file: string): void {
  if (isUnderKernel(file)) return;
  if (file.includes(`${path.sep}scripts${path.sep}`)) return;

  const normalized = path.normalize(file);
  const text = fs.readFileSync(file, "utf8");
  const relPath = rel(file);

  if (text.includes('from "@/lib/store"') || text.includes("from '@/lib/store'")) {
    errors.push(`${relPath}: import @/lib/store — use @/cnexus-kernel`);
  }

  if (
    (text.includes('from "@/hooks/useMindOverview"') ||
      text.includes("from '@/hooks/useMindOverview'")) &&
    !relPath.startsWith("hooks/useMindOverview.ts")
  ) {
    errors.push(`${relPath}: import useMindOverview shim — use @/cnexus-kernel`);
  }

  if (/brain_memory|\/core\/|runtime\.py/.test(text)) {
    errors.push(`${relPath}: must not reference Python core paths`);
  }

  if (!ALLOWED_LIB.has(normalized) && relPath.startsWith("lib/")) {
    if (text.includes("mindOverview(") || text.includes("connectStateStream(")) {
      errors.push(`${relPath}: Runtime API calls belong in cnexus-kernel only`);
    }
  }

  if (relPath.startsWith("components/") || relPath.startsWith("app/")) {
    if (text.includes("mindOverview(") || text.includes("connectStateStream(")) {
      errors.push(`${relPath}: direct Runtime fetch/WS — use useMindOverview / kernel bridge`);
    }
    if (text.includes("new WebSocket(")) {
      errors.push(`${relPath}: WebSocket must live in cnexus-kernel/MindRuntimeBridge`);
    }
  }
}

for (const dir of SCAN_DIRS) {
  for (const file of walk(path.join(ROOT, dir))) {
    checkFile(file);
  }
}

if (errors.length) {
  console.error("Kernel boundary violations:\n");
  for (const err of errors) console.error(`  - ${err}`);
  process.exit(1);
}

console.log("Kernel boundary: OK");
