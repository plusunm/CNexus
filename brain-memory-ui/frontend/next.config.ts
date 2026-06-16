import type { NextConfig } from "next";

const isTauri = process.env.CNEXUS_TAURI === "1";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: isTauri ? "export" : "standalone",
  images: { unoptimized: isTauri },
  env: {
    NEXT_PUBLIC_CNEXUS_RELEASE: process.env.CNEXUS_RELEASE ?? "",
  },
};

export default nextConfig;
