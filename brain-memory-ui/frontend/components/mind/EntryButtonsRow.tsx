"use client";

import { Database, MessageSquare, Upload } from "lucide-react";
import { useMindTheme } from "./MindUiProvider";

export function EntryButtonsRow() {
  const t = useMindTheme();

  const entries = [
    {
      id: "chat-panel",
      icon: MessageSquare,
      color: t.blue,
      bg: t.blueSoft,
      title: "进入对话",
      desc: "与我的心智对话，探索思考",
    },
    {
      id: "memory-panel",
      icon: Database,
      color: t.blue,
      bg: t.blueSoft,
      title: "浏览记忆",
      desc: "查看和管理我的记忆内容",
    },
    {
      id: "import",
      icon: Upload,
      color: t.green,
      bg: t.greenSoft,
      title: "导入数据",
      desc: "上传文档和数据到我的记忆",
    },
  ];

  const scrollTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
      {entries.map(({ id, icon: Icon, color, bg, title, desc }) => (
        <button
          key={title}
          type="button"
          onClick={() => scrollTo(id)}
          className="flex items-center gap-3 p-4 rounded-xl border text-left transition hover:shadow-md"
          style={{
            backgroundColor: bg,
            borderColor: `${color}33`,
            borderLeftWidth: 4,
            borderLeftColor: color,
          }}
        >
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0 text-white"
            style={{ backgroundColor: color }}
          >
            <Icon className="w-5 h-5" />
          </div>
          <div>
            <p className="text-sm font-semibold" style={{ color: t.text }}>
              {title}
            </p>
            <p className="text-xs mt-0.5" style={{ color: t.textMuted }}>
              {desc}
            </p>
          </div>
        </button>
      ))}
    </div>
  );
}
