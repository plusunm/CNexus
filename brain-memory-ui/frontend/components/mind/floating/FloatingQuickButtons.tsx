"use client";



import { Database, MessageSquare, Upload } from "lucide-react";

import { floatTy } from "@/lib/floatTypography";

import { useMindTheme } from "../MindUiProvider";

import type { FloatPanel } from "@/lib/floatingBarStorage";



type Props = {

  activePanel: FloatPanel | null;

  onSelect: (panel: FloatPanel) => void;

  canChat?: boolean;

  canUpload?: boolean;

  statusHint?: string | null;

};



export function FloatingQuickButtons({

  activePanel,

  onSelect,

  canChat = true,

  canUpload = true,

  statusHint,

}: Props) {

  const t = useMindTheme();



  const buttons: {

    id: FloatPanel;

    icon: typeof MessageSquare;

    label: string;

    color: string;

    enabled: boolean;

  }[] = [

    { id: "chat", icon: MessageSquare, label: "对话", color: t.blue, enabled: canChat },

    { id: "memory", icon: Database, label: "记忆", color: t.purple, enabled: canChat },

    { id: "upload", icon: Upload, label: "导入", color: t.green, enabled: canUpload },

  ];



  return (

    <div className="flex flex-col shrink-0 min-h-0 overflow-hidden" data-no-drag>

      {statusHint && (

        <p

          className={`px-3 pt-1 pb-0.5 ${floatTy.caption} min-w-0 max-w-full overflow-hidden text-ellipsis whitespace-nowrap shrink-0 leading-tight`}

          style={{ color: t.orange }}

          role="status"

          title={statusHint}

        >

          {statusHint}

        </p>

      )}

      <div className="flex items-center gap-2 px-3 py-2 shrink-0">

        {buttons.map(({ id, icon: Icon, label, color, enabled }) => {

          const active = activePanel === id;

          return (

            <button

              key={id}

              type="button"

              disabled={!enabled}

              onClick={() => onSelect(id)}

              className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl ${floatTy.tab} transition active:scale-[0.98] disabled:opacity-45 disabled:cursor-not-allowed`}

              style={{

                backgroundColor: active ? `${color}22` : "rgba(255,255,255,0.04)",

                color: active ? color : enabled ? t.textMuted : t.textLight,

                border: `1px solid ${active ? `${color}55` : t.border}`,

              }}

              aria-pressed={active}

            >

              <Icon className="w-3.5 h-3.5" />

              {label}

            </button>

          );

        })}

      </div>

    </div>

  );

}


