"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home,
  Database,
  MessageSquare,
  Upload,
  Target,
  Lightbulb,
  Sparkles,
  Shield,
  Settings,
} from "lucide-react";
import clsx from "clsx";
import { useMindOverview } from "@/cnexus-kernel";
import { CnexusAvatarIcon } from "./CnexusAvatarIcon";
import { useMindTheme } from "./MindUiProvider";

const NAV = [
  { href: "/", label: "首页", sub: "Mind", icon: Home },
  { href: "/shell?panel=memory&layout=float", label: "Memory", icon: Database },
  { href: "/shell?panel=chat&layout=float", label: "Chat", icon: MessageSquare },
  { href: "/#import", label: "Upload", icon: Upload },
  { href: "/#goals", label: "Goals", icon: Target },
  { href: "/#beliefs", label: "Beliefs", icon: Lightbulb },
  { href: "/#reflections", label: "Reflections", icon: Sparkles },
  { href: "/#governance", label: "Governance", icon: Shield },
  { href: "/models", label: "Settings", icon: Settings },
];

export function MindSidebar() {
  const t = useMindTheme();
  const pathname = usePathname();
  const { signals } = useMindOverview();

  return (
    <aside
      className="w-[76px] shrink-0 flex flex-col items-center py-4 border-r min-h-screen"
      style={{ backgroundColor: t.surface, borderColor: t.border }}
    >
      <div className="flex flex-col items-center gap-1 mb-5 px-1">
        <CnexusAvatarIcon size={40} rounded="xl" />
        <span className="text-[10px] font-bold tracking-tight" style={{ color: t.purple }}>
          CNexus
        </span>
      </div>
      <nav className="flex flex-col gap-0.5 w-full px-1.5 flex-1">
        {NAV.map(({ href, label, sub, icon: Icon }) => {
          const base = href.split("#")[0];
          const active =
            href === "/"
              ? pathname === "/"
              : base !== "/" && pathname.startsWith(base);
          return (
            <Link
              key={href}
              href={href}
              title={sub ? `${label} (${sub})` : label}
              className={clsx(
                "flex flex-col items-center gap-0.5 py-2 rounded-lg text-[9px] transition",
                active ? "font-semibold" : "hover:bg-gray-50"
              )}
              style={{
                backgroundColor: active ? t.sidebarActive : undefined,
                color: active ? t.purple : t.textMuted,
              }}
            >
              <Icon className="w-[18px] h-[18px]" strokeWidth={active ? 2.2 : 1.8} />
              <span className="leading-tight text-center">{label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto flex flex-col items-center gap-1 px-1 pt-4">
        <span
          className="w-2 h-2 rounded-full"
          style={{
            backgroundColor:
              signals.health.source === "runtime"
                ? t.green
                : signals.health.source === "demo"
                  ? t.orange
                  : t.red,
          }}
        />
        <span className="text-[8px]" style={{ color: t.textLight }}>
          {signals.health.connectionLabel}
        </span>
      </div>
    </aside>
  );
}
