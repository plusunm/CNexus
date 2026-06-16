/** True when built with CNEXUS_RELEASE=1 (installer / tauri:build). */
export const isReleaseBuild = process.env.NEXT_PUBLIC_CNEXUS_RELEASE === "1";
