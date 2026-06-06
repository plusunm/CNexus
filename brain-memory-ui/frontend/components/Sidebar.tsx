import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";

const links = [
  { href: "/", label: "仪表盘" },
  { href: "/chat", label: "对话" },
  { href: "/memory", label: "记忆" },
  { href: "/models", label: "模型" },
];

export function Sidebar({ apiOnline }: { apiOnline: boolean }) {
  const pathname = usePathname();

  return (
    <aside className="w-64 shrink-0 border-r border-border bg-surface flex flex-col p-4 gap-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent to-accent2 flex items-center justify-center text-lg">
          🧠
        </div>
        <div>
          <div className="font-bold text-sm">Brain-Memory G1</div>
          <div className="text-xs text-gray-400">brain-memory-ui</div>
        </div>
      </div>

      <nav className="flex flex-col gap-1">
        {links.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className={clsx(
              "px-3 py-2 rounded-lg text-sm transition",
              pathname === l.href ? "bg-accent text-white font-medium" : "text-gray-400 hover:bg-bg hover:text-white"
            )}
          >
            {l.label}
          </Link>
        ))}
      </nav>

      <div className="mt-auto flex items-center gap-2 text-xs text-gray-400">
        <span className={clsx("w-2 h-2 rounded-full", apiOnline ? "bg-green-500" : "bg-red-500")} />
        API {apiOnline ? "在线" : "离线"}
      </div>
    </aside>
  );
}
