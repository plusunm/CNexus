/** CNexus avatar icon for Tauri bundle — matches UI CnexusAvatarIcon (gradient + sparkles). */
import { writeFileSync, mkdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import zlib from "zlib";

const __dir = dirname(fileURLToPath(import.meta.url));
const outDir = join(__dir, "..", "src-tauri", "icons");
mkdirSync(outDir, { recursive: true });

const BLUE = { r: 47, g: 107, b: 255 };
const PURPLE = { r: 138, g: 92, b: 255 };

function crc32(buf) {
  let c = ~0;
  for (let i = 0; i < buf.length; i++) {
    c ^= buf[i];
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  }
  return ~c >>> 0;
}

function chunk(type, data) {
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length);
  const t = Buffer.from(type);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(Buffer.concat([t, data])));
  return Buffer.concat([len, t, data, crc]);
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

function gradientAt(x, y, size) {
  const t = Math.min(1, Math.max(0, (x + y) / (2 * (size - 1))));
  return {
    r: Math.round(lerp(BLUE.r, PURPLE.r, t)),
    g: Math.round(lerp(BLUE.g, PURPLE.g, t)),
    b: Math.round(lerp(BLUE.b, PURPLE.b, t)),
  };
}

function insideRoundedRect(x, y, size, pad, radius) {
  const left = pad;
  const top = pad;
  const right = size - pad - 1;
  const bottom = size - pad - 1;
  if (x < left || x > right || y < top || y > bottom) return false;
  const cx = (left + right) / 2;
  const cy = (top + bottom) / 2;
  const hw = (right - left) / 2;
  const hh = (bottom - top) / 2;
  const qx = Math.abs(x - cx) - hw + radius;
  const qy = Math.abs(y - cy) - hh + radius;
  if (qx <= 0 || qy <= 0) return true;
  return qx * qx + qy * qy <= radius * radius;
}

function pointInStar(px, py, cx, cy, outerR, innerR, points = 4, rotation = -Math.PI / 2) {
  const dx = px - cx;
  const dy = py - cy;
  const dist = Math.hypot(dx, dy);
  if (dist > outerR) return false;
  let angle = Math.atan2(dy, dx) - rotation;
  while (angle < 0) angle += Math.PI * 2;
  while (angle >= Math.PI * 2) angle -= Math.PI * 2;
  const sector = (Math.PI * 2) / points;
  const local = angle % sector;
  const half = sector / 2;
  const t = local <= half ? local / half : (sector - local) / half;
  const allowed = innerR + (outerR - innerR) * t;
  return dist <= allowed;
}

function sparkleMask(x, y, size) {
  const s = size;
  const main = pointInStar(x, y, s * 0.46, s * 0.52, s * 0.17, s * 0.07, 4);
  const small = pointInStar(x, y, s * 0.72, s * 0.3, s * 0.08, s * 0.035, 4, -Math.PI / 4);
  const dot = Math.hypot(x - s * 0.32, y - s * 0.72) <= s * 0.045;
  return main || small || dot;
}

function png(size) {
  const pad = Math.round(size * 0.08);
  const radius = Math.round(size * 0.22);
  const raw = Buffer.alloc((size * 4 + 1) * size);

  for (let y = 0; y < size; y++) {
    raw[y * (size * 4 + 1)] = 0;
    for (let x = 0; x < size; x++) {
      const i = y * (size * 4 + 1) + 1 + x * 4;
      if (!insideRoundedRect(x, y, size, pad, radius)) {
        raw[i + 3] = 0;
        continue;
      }
      if (sparkleMask(x, y, size)) {
        raw[i] = 255;
        raw[i + 1] = 255;
        raw[i + 2] = 255;
        raw[i + 3] = 255;
        continue;
      }
      const c = gradientAt(x, y, size);
      raw[i] = c.r;
      raw[i + 1] = c.g;
      raw[i + 2] = c.b;
      raw[i + 3] = 255;
    }
  }

  const sig = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(size, 0);
  ihdr.writeUInt32BE(size, 4);
  ihdr[8] = 8;
  ihdr[9] = 6;
  return Buffer.concat([
    sig,
    chunk("IHDR", ihdr),
    chunk("IDAT", zlib.deflateSync(raw, { level: 9 })),
    chunk("IEND", Buffer.alloc(0)),
  ]);
}

for (const size of [32, 128, 256]) {
  writeFileSync(join(outDir, `${size}x${size}.png`), png(size));
}
writeFileSync(join(outDir, "128x128@2x.png"), png(256));
writeFileSync(join(outDir, "icon.png"), png(256));

const appIconDir = join(__dir, "..", "app");
mkdirSync(appIconDir, { recursive: true });
writeFileSync(join(appIconDir, "icon.png"), png(256));
console.log("Wrote CNexus avatar Tauri icons to", outDir);
console.log("Wrote Next.js app/icon.png");
