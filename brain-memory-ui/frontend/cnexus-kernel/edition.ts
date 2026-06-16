/**
 * CNexus edition — personal vs enterprise in ONE installer.
 * Resolved at runtime from cnexus-config.json (installer) or local activation.
 */

export type CnexusEdition = "personal" | "enterprise";

export type EditionProfile = {
  id: CnexusEdition;
  productName: string;
  shortLabel: string;
  allowDemo: boolean;
  allowRuntimeConnect: boolean;
  requireRuntime: boolean;
  showModeGate: boolean;
  modelsAdmin: boolean;
  bundledRuntime: boolean;
  licenseRequired: boolean;
};

const EDITION_STORAGE_KEY = "cnexus-edition";
const LICENSE_STORAGE_KEY = "cnexus-license";

/** Unified installer binary — edition is NOT baked at build time. */
let activeEdition: CnexusEdition = "personal";

export function parseEdition(value: unknown): CnexusEdition {
  return value === "enterprise" ? "enterprise" : "personal";
}

export function setEdition(edition: CnexusEdition): void {
  activeEdition = edition;
}

export function getEdition(): CnexusEdition {
  return activeEdition;
}

export function loadStoredEdition(): CnexusEdition | null {
  if (typeof window === "undefined") return null;
  const v = localStorage.getItem(EDITION_STORAGE_KEY);
  if (v === "enterprise" || v === "personal") return v;
  return null;
}

export function saveStoredEdition(edition: CnexusEdition): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(EDITION_STORAGE_KEY, edition);
}

export function loadStoredLicense(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(LICENSE_STORAGE_KEY)?.trim() ?? "";
}

export function saveStoredLicense(license: string): void {
  if (typeof window === "undefined") return;
  const v = license.trim();
  if (v) localStorage.setItem(LICENSE_STORAGE_KEY, v);
  else localStorage.removeItem(LICENSE_STORAGE_KEY);
}

/** Apply installer config + optional local enterprise activation. */
export function resolveEdition(configEdition?: unknown, storedEdition?: CnexusEdition | null): CnexusEdition {
  if (configEdition === "enterprise") return "enterprise";
  if (storedEdition === "enterprise") return "enterprise";
  return "personal";
}

export const EDITION_PROFILES: Record<CnexusEdition, EditionProfile> = {
  personal: {
    id: "personal",
    productName: "CNexus",
    shortLabel: "个人版",
    allowDemo: true,
    allowRuntimeConnect: true,
    requireRuntime: false,
    showModeGate: true,
    modelsAdmin: false,
    bundledRuntime: true,
    licenseRequired: false,
  },
  enterprise: {
    id: "enterprise",
    productName: "CNexus",
    shortLabel: "企业版",
    allowDemo: false,
    allowRuntimeConnect: true,
    requireRuntime: true,
    showModeGate: false,
    modelsAdmin: true,
    bundledRuntime: true,
    licenseRequired: true,
  },
};

export function getEditionProfile(edition: CnexusEdition = getEdition()): EditionProfile {
  return EDITION_PROFILES[edition];
}

export function defaultConnectionPreference(
  edition: CnexusEdition = getEdition(),
  options?: { tauriDesktop?: boolean },
): "demo" | "runtime" | null {
  const profile = getEditionProfile(edition);
  if (profile.requireRuntime) return "runtime";
  // Desktop installer: sidecar auto-starts — skip tiny-window mode gate, default Live.
  if (options?.tauriDesktop && profile.bundledRuntime && profile.allowRuntimeConnect) {
    return "runtime";
  }
  if (!profile.showModeGate && profile.allowDemo) return "demo";
  return null;
}
