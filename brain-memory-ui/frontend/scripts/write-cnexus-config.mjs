import fs from "node:fs";
import path from "node:path";

/** Release installer → enterprise (no Demo). Dev → personal unless overridden. */
const editionArg = process.argv[2];
const isRelease = process.env.CNEXUS_RELEASE === "1" || editionArg === "enterprise" || editionArg === "release";
const edition =
  editionArg === "personal"
    ? "personal"
    : editionArg === "enterprise" || editionArg === "release" || process.env.CNEXUS_EDITION === "enterprise" || isRelease
      ? "enterprise"
      : "personal";

const apiBase = process.env.CNEXUS_API_BASE ?? "http://127.0.0.1:8000";
const wsBase = process.env.CNEXUS_WS_BASE ?? apiBase.replace(/^http/, "ws");
const apiToken = process.env.CNEXUS_API_TOKEN ?? "";

const cfg = {
  edition,
  apiBase,
  wsBase,
};
if (apiToken) Object.assign(cfg, { apiToken });

const out = path.join(process.cwd(), "public", "cnexus-config.json");
fs.writeFileSync(out, `${JSON.stringify(cfg)}\n`, "utf8");
console.log(`Wrote ${out} (unified installer, edition=${edition})`);
