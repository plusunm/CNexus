"use client";

import type { ExecutionIdentityBundleView, SpineFrontContractV1 } from "@/lib/spine/contract";
import { bi, biSection, spineL } from "@/lib/spine/labels";
import { useMindTheme } from "../../MindUiProvider";

type Props = {
  identity: ExecutionIdentityBundleView | null;
  contract: SpineFrontContractV1;
};

export function SpineIdentityPanel({ identity, contract }: Props) {
  const t = useMindTheme();
  const explain = contract.explanation.explain_v3;

  if (!identity) {
    return (
      <section className="p-4 border-t text-[11px]" style={{ borderColor: t.border, color: t.textMuted }}>
        {bi(spineL.noIdentity)}
      </section>
    );
  }

  const sig = identity.signatures;

  return (
    <section className="p-4 border-t shrink-0" style={{ borderColor: t.border, backgroundColor: `${t.purpleSoft}11` }}>
      <h3 className="text-[10px] uppercase tracking-wider mb-3 opacity-60" style={{ color: t.textMuted }}>
        {biSection(spineL.identityPanelDetail)}
      </h3>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 mb-4 text-[10px] font-mono">
        <SigCell label={bi(spineL.sigGraph)} value={sig.graph} t={t} />
        <SigCell label={bi(spineL.sigState)} value={sig.state} t={t} />
        <SigCell label={bi(spineL.sigControl)} value={sig.control} t={t} />
        <SigCell label={bi(spineL.sigCausal)} value={sig.causal} t={t} />
      </div>

      <div className="grid lg:grid-cols-2 gap-4 mb-4">
        <div>
          <p className="text-[10px] uppercase opacity-60 mb-1" style={{ color: t.textMuted }}>
            {bi(spineL.identityEquivalent)}
          </p>
          {identity.equivalent_traces.length ? (
            <ul className="text-[11px] font-mono space-y-0.5" style={{ color: t.green }}>
              {identity.equivalent_traces.map((tid) => (
                <li key={tid}>· {tid}</li>
              ))}
            </ul>
          ) : (
            <p className="text-[11px] opacity-50" style={{ color: t.textMuted }}>
              —
            </p>
          )}
        </div>
        <div>
          <p className="text-[10px] uppercase opacity-60 mb-1" style={{ color: t.textMuted }}>
            {bi(spineL.identityDriftVariants)}
          </p>
          {identity.drift_variants.length ? (
            <ul className="text-[11px] font-mono space-y-0.5" style={{ color: t.orange }}>
              {identity.drift_variants.map((tid) => (
                <li key={tid}>· {tid}</li>
              ))}
            </ul>
          ) : (
            <p className="text-[11px] opacity-50" style={{ color: t.textMuted }}>
              none
            </p>
          )}
        </div>
      </div>

      <div className="rounded-lg border px-3 py-2.5" style={{ borderColor: t.border, backgroundColor: t.chatBg }}>
        <p className="text-[10px] uppercase opacity-60 mb-1" style={{ color: t.textMuted }}>
          {bi(spineL.identityExplanation)}
        </p>
        <p className="text-sm leading-relaxed" style={{ color: t.text }}>
          {identity.identity_note ?? explain?.summary ?? contract.explanation.narrative}
        </p>
        {explain?.caveats?.length ? (
          <ul className="mt-2 text-[10px] space-y-0.5" style={{ color: t.orange }}>
            {explain.caveats.map((c, i) => (
              <li key={i}>· {c}</li>
            ))}
          </ul>
        ) : null}
      </div>
    </section>
  );
}

function SigCell({
  label,
  value,
  t,
}: {
  label: string;
  value: string;
  t: ReturnType<typeof useMindTheme>;
}) {
  return (
    <div className="rounded border px-2 py-1.5" style={{ borderColor: t.border }}>
      <div className="opacity-50 truncate">{label}</div>
      <div className="truncate" style={{ color: "#5eead4" }}>
        {value}
      </div>
    </div>
  );
}
