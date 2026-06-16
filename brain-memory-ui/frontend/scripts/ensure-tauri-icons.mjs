/**
 * Skip slow `tauri icon` when bundle icons already exist.
 * Regenerates only when icon.png is new or icon.ico is missing.
 */
import { existsSync } from "fs";
import { execSync } from "child_process";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const iconsDir = join(root, "src-tauri", "icons");
const sourceIcon = join(iconsDir, "icon.png");
const force = process.argv.includes("--force");

function run(cmd) {
  console.log(`>> ${cmd}`);
  execSync(cmd, { cwd: root, stdio: "inherit", env: process.env });
}

const required = [
  "icon.ico",
  "icon.icns",
  "32x32.png",
  "128x128.png",
  "128x128@2x.png",
];

if (!existsSync(sourceIcon)) {
  run("node scripts/generate-tauri-icons.mjs");
}

const needTauriIcon =
  force || required.some((name) => !existsSync(join(iconsDir, name)));

if (needTauriIcon) {
  console.log("Generating platform icons (tauri icon, ~5-30s)...");
  run("npx tauri icon src-tauri/icons/icon.png");
} else {
  console.log("Icons up to date — skipped tauri icon");
}
