"use client";

import { useEffect, useState } from "react";
import { KeyRound, ShieldAlert } from "lucide-react";
import { listen } from "@tauri-apps/api/event";
import {
  runSecurityBootstrapPreflight,
  type SecurityBootstrapResult,
} from "@/lib/securityBootstrap";
import { isTauriDesktop } from "@/lib/tauriDesktop";
import { overviewTheme } from "@/components/mind/themes/overviewTheme";

type Props = {
  children: React.ReactNode;
};

/**
 * Desktop-only gate: listen for bootstrap failures and show a non-crashing UI.
 */
export function SecurityBootstrapGate({ children }: Props) {
  const t = overviewTheme;
  const [blocked, setBlocked] = useState<SecurityBootstrapResult | null>(null);

  useEffect(() => {
    if (!isTauriDesktop()) return;

    let cancelled = false;

    const apply = (result: SecurityBootstrapResult) => {
      if (!result.ok) setBlocked(result);
    };

    void runSecurityBootstrapPreflight(false).then((result) => {
      if (!cancelled) apply(result);
    });

    const unsubs: Array<() => void> = [];
    void (async () => {
      unsubs.push(
        await listen<SecurityBootstrapResult>("cnexus:security-bootstrap-failed", (event) => {
          apply(event.payload);
        }),
      );
      unsubs.push(
        await listen<SecurityBootstrapResult>("cnexus:security-bootstrap-ok", () => {
          if (!cancelled) setBlocked(null);
        }),
      );
    })();

    return () => {
      cancelled = true;
      unsubs.forEach((fn) => fn());
    };
  }, []);

  if (!blocked) {
    return <>{children}</>;
  }

  return (
    <div
      className="w-full h-full min-h-[228px] flex flex-col items-center justify-center gap-3 p-4 text-center select-none"
      style={{
        background: "linear-gradient(160deg, #1e1e24 0%, #121216 100%)",
        color: t.textMuted,
        fontFamily: t.fontSans,
      }}
      data-cnexus-security-blocked="true"
    >
      <ShieldAlert className="w-8 h-8 text-amber-400" aria-hidden />
      <p className="text-sm font-medium text-zinc-200">CNexus 安全启动受限</p>
      <p className="text-xs text-zinc-400 max-w-sm leading-relaxed">{blocked.user_message}</p>
      <p className="text-[10px] text-zinc-500 font-mono">
        {blocked.internal_code} · {blocked.runtime_mode}
      </p>
      {blocked.machine_fingerprint ? (
        <p className="text-[10px] text-zinc-500 font-mono break-all max-w-xs">
          设备指纹：{blocked.machine_fingerprint}
        </p>
      ) : null}
      {blocked.issues.length > 0 ? (
        <ul className="text-[10px] text-zinc-500 max-w-sm text-left list-disc pl-4 space-y-1">
          {blocked.issues.slice(0, 4).map((issue) => (
            <li key={`${issue.code}-${issue.detail}`}>
              <span className="text-zinc-400">{issue.code}</span> — {issue.detail}
            </li>
          ))}
        </ul>
      ) : null}
      <div className="flex items-center gap-2 text-xs text-indigo-300">
        <KeyRound className="w-3.5 h-3.5" aria-hidden />
        <span>请在设置中重新激活企业 License，或联系管理员换机。</span>
      </div>
    </div>
  );
}
