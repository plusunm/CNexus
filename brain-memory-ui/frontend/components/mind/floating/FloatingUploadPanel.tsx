"use client";

import { FileStack, FileText, Link2, Upload, UploadCloud } from "lucide-react";
import { useEmbeddingStatus } from "@/hooks/useEmbeddingStatus";
import { useMemoryImport, FLOAT_LAYER_OPTIONS, type ImportTab } from "@/hooks/useMemoryImport";
import { DOCUMENT_ACCEPT } from "@/lib/documentIngest";
import { bi, floatL } from "@/lib/spine/labels";
import { floatTy } from "@/lib/floatTypography";
import { EmbeddingModeBadge } from "../EmbeddingModeBadge";
import { useMindTheme } from "../MindUiProvider";
import { FloatSelect } from "./FloatSelect";

const FLOAT_TABS: { id: ImportTab; label: string; icon: typeof UploadCloud }[] = [
  { id: "文档导入", label: "文档", icon: UploadCloud },
  { id: "文本导入", label: "文本", icon: FileText },
  { id: "URL 导入", label: "链接", icon: Link2 },
  { id: "批量导入", label: "批量", icon: FileStack },
];

export function FloatingUploadPanel() {
  const t = useMindTheme();
  const embeddingStatus = useEmbeddingStatus();
  const imp = useMemoryImport({ deferFileCapture: true });

  const noteColor =
    imp.importNote?.includes("失败") || imp.importNote?.includes("请先")
      ? t.orange
      : imp.importNote?.includes("已")
        ? t.green
        : t.textMuted;

  return (
    <div
      className="cnexus-float-panel flex flex-col h-full min-h-0 min-w-0 overflow-hidden"
      style={{ backgroundColor: t.surface, borderColor: t.border }}
      data-cnexus-float-upload
    >
      <header
        className="shrink-0 flex items-center gap-2 px-3 py-2 border-b"
        style={{ borderColor: t.border }}
        data-no-drag
      >
        <Upload className="w-3.5 h-3.5 shrink-0" style={{ color: t.green }} />
        <span className={`${floatTy.label} truncate`} style={{ color: t.text }}>
          {bi(floatL.importPanel)}
        </span>
        {imp.isDemo && (
          <span
            className={`${floatTy.caption} ml-auto shrink-0 px-1.5 py-0.5 rounded`}
            style={{ color: t.purple, backgroundColor: `${t.purple}18` }}
          >
            Demo
          </span>
        )}
      </header>

      <div
        className="shrink-0 grid grid-cols-4 gap-1 px-3 pt-2 pb-1.5 border-b"
        style={{ borderColor: t.border }}
        data-no-drag
      >
        {FLOAT_TABS.map(({ id, label, icon: Icon }) => {
          const active = imp.tab === id;
          return (
            <button
              key={id}
              type="button"
              className={`flex flex-col items-center gap-0.5 rounded-lg py-1.5 px-1 transition ${floatTy.caption}`}
              style={{
                color: active ? t.green : t.textMuted,
                backgroundColor: active ? `${t.green}18` : "transparent",
                border: `1px solid ${active ? `${t.green}44` : "transparent"}`,
              }}
              onClick={() => imp.selectTab(id)}
            >
              <Icon className="w-3.5 h-3.5" />
              <span className="font-medium">{label}</span>
            </button>
          );
        })}
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto cnexus-float-scroll px-3 py-3" data-no-drag>
        {imp.tab === "文档导入" && (
          <label
            className={`flex flex-col items-center justify-center gap-1.5 py-8 rounded-xl border border-dashed transition ${
              !imp.canImport && !imp.isDemo
                ? "opacity-55 cursor-not-allowed pointer-events-none"
                : "cursor-pointer"
            }`}
            style={{ borderColor: `${t.green}44`, backgroundColor: `${t.green}10` }}
          >
            <UploadCloud className="w-6 h-6" style={{ color: t.green }} />
            <span className={`${floatTy.body} text-center`} style={{ color: t.text }}>
              点击选择文件
            </span>
            <span className={floatTy.caption} style={{ color: t.textMuted }}>
              PDF · Word · TXT · Markdown
            </span>
            <input
              ref={imp.docInputRef}
              type="file"
              multiple
              accept={DOCUMENT_ACCEPT}
              className="hidden"
              onChange={(e) => void imp.onFiles(e.target.files, e.currentTarget)}
            />
          </label>
        )}

        {imp.tab === "文本导入" && (
          <textarea
            className={`w-full min-h-[160px] border rounded-xl px-3 py-2 resize-none outline-none cnexus-float-scroll ${floatTy.input}`}
            style={{ borderColor: t.border, backgroundColor: t.bg, color: t.text }}
            placeholder="粘贴笔记、会议纪要、代码片段…"
            value={imp.textContent}
            onChange={(e) => imp.setTextContent(e.target.value)}
          />
        )}

        {imp.tab === "URL 导入" && (
          <div className="space-y-2">
            <input
              className={`w-full border rounded-xl px-3 py-2.5 outline-none ${floatTy.input}`}
              style={{ borderColor: t.border, backgroundColor: t.bg, color: t.text }}
              placeholder="https://example.com/article"
              value={imp.urlValue}
              onChange={(e) => imp.setUrlValue(e.target.value)}
            />
            <p className={floatTy.caption} style={{ color: t.textMuted }}>
              写入链接标记；正文抓取由 Runtime 后续处理。
            </p>
          </div>
        )}

        {imp.tab === "批量导入" && (
          <div className="space-y-2">
            <label
              className={`flex items-center justify-center gap-2 py-3 rounded-xl border border-dashed cursor-pointer ${
                !imp.canImport && !imp.isDemo ? "opacity-60" : ""
              }`}
              style={{ borderColor: `${t.green}44`, backgroundColor: `${t.green}10` }}
            >
              <UploadCloud className="w-4 h-4" style={{ color: t.green }} />
              <span className={floatTy.body} style={{ color: t.textMuted }}>
                选择多个文件
              </span>
              <input
                ref={imp.batchInputRef}
                type="file"
                multiple
                accept={DOCUMENT_ACCEPT}
                className="hidden"
                onChange={(e) => void imp.onFiles(e.target.files, e.currentTarget)}
              />
            </label>
            <textarea
              className={`w-full min-h-[100px] border rounded-xl px-3 py-2 resize-none outline-none cnexus-float-scroll ${floatTy.input}`}
              style={{ borderColor: t.border, backgroundColor: t.bg, color: t.text }}
              placeholder={"每行一个 URL\nhttps://a.com\nhttps://b.com/doc"}
              value={imp.batchUrls}
              onChange={(e) => imp.setBatchUrls(e.target.value)}
            />
          </div>
        )}

        {imp.files.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {imp.files.slice(-4).map((f, i) => (
              <span
                key={`${f.name}-${i}`}
                className={`${floatTy.caption} max-w-full truncate px-2 py-0.5 rounded-md`}
                style={{ color: t.textMuted, backgroundColor: "rgba(255,255,255,0.06)" }}
              >
                {f.name}
              </span>
            ))}
            {imp.files.length > 4 && (
              <span className={floatTy.caption} style={{ color: t.textLight }}>
                +{imp.files.length - 4}
              </span>
            )}
            <button
              type="button"
              className={`${floatTy.caption} px-1.5 py-0.5 rounded`}
              style={{ color: t.orange }}
              onClick={imp.clearFiles}
            >
              清空
            </button>
          </div>
        )}
      </div>

      <footer
        className="shrink-0 border-t px-3 py-2.5 space-y-2"
        style={{ borderColor: t.border, backgroundColor: "rgba(0,0,0,0.1)" }}
        data-no-drag
      >
        <div className="grid grid-cols-2 gap-2">
          <FloatSelect
            label="记忆层"
            value={imp.layer}
            options={[...FLOAT_LAYER_OPTIONS]}
            onChange={imp.setLayer}
            menuPortal
          />
          <FloatSelect
            label="关联目标"
            value={imp.activeGoal}
            options={imp.goalSelectOptions}
            onChange={imp.setRelatedGoal}
            menuPortal
          />
        </div>

        {imp.layer === "episodic" && embeddingStatus && (
          <div className={`${floatTy.caption} flex items-center gap-1.5`} style={{ color: t.textLight }}>
            <EmbeddingModeBadge status={embeddingStatus} compact />
            <span className="truncate">经历向量 · 保存不触发反思</span>
          </div>
        )}

        {imp.statusHint && (
          <p
            className={`${floatTy.caption} px-2 py-1.5 rounded-md border`}
            style={{ color: t.orange, borderColor: `${t.orange}44`, backgroundColor: t.orangeSoft }}
            role="status"
          >
            {imp.statusHint}
          </p>
        )}

        {imp.importNote && (
          <p className={`${floatTy.caption} truncate`} style={{ color: noteColor }}>
            {imp.importNote}
          </p>
        )}

        <button
          type="button"
          className={`w-full py-2 rounded-lg ${floatTy.btn} text-white disabled:opacity-55 transition-transform active:scale-[0.98]`}
          style={{ backgroundColor: t.green }}
          disabled={imp.importing || (!imp.canImport && !imp.isDemo)}
          aria-busy={imp.importing}
          onClick={() => void imp.startImport()}
        >
          {imp.importing ? "导入中…" : imp.importButtonLabel}
        </button>
      </footer>
    </div>
  );
}
