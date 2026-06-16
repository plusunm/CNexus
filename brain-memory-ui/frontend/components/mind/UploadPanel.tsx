"use client";

import { useEmbeddingStatus } from "@/hooks/useEmbeddingStatus";
import {
  useMemoryImport,
  LAYER_OPTIONS,
  type ImportTab,
} from "@/hooks/useMemoryImport";
import { DOCUMENT_ACCEPT } from "@/lib/documentIngest";
import { FileStack, FileText, Link2, UploadCloud } from "lucide-react";
import { EmbeddingModeBadge } from "./EmbeddingModeBadge";
import { useMindTheme } from "./MindUiProvider";

type PanelVariant = "overview" | "cognitive" | "float";

export function UploadPanel({
  variant = "overview",
  excludeDocImport = false,
}: {
  variant?: PanelVariant;
  /** Mind 概览：文档上传已在工作台，此处只保留高级导入 */
  excludeDocImport?: boolean;
}) {
  const t = useMindTheme();
  const isCognitive = variant === "cognitive";
  const ty = {
    body: "text-xs",
    label: "text-xs font-medium",
    input: "text-xs",
    caption: "text-[10px]",
    tab: "text-xs",
    btn: "text-sm font-medium text-white",
    mono: "text-[11px]",
  };
  const embeddingStatus = useEmbeddingStatus();
  const imp = useMemoryImport({ excludeDocImport });

  const scrollAreaClass =
    variant === "overview"
      ? "flex flex-col gap-3 p-4 overflow-hidden"
      : "flex-1 overflow-y-auto";

  const panelHeightClass =
    variant === "overview"
      ? "h-[360px] rounded-xl border"
      : "h-[420px] rounded-xl border";

  const renderTabBody = () => {
    if (imp.tab === "文档导入") {
      return (
        <label
          className={`flex flex-col items-center justify-center gap-2 p-6 rounded-xl border-2 border-dashed cursor-pointer ${
            !imp.canImport && !imp.isDemo ? "opacity-60" : ""
          }`}
          style={{ borderColor: `${t.green}44`, backgroundColor: t.greenSoft }}
        >
          <UploadCloud className="w-7 h-7" style={{ color: t.green }} />
          <span className={`${ty.label} text-center`} style={{ color: t.textMuted }}>
            拖拽 PDF / Word / TXT / Markdown
            <br />
            或点击选择文件
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
      );
    }

    if (imp.tab === "文本导入") {
      return (
        <div className="flex flex-col gap-2 flex-1 min-h-[140px]">
          <div className={`flex items-center gap-1.5 ${ty.label}`} style={{ color: t.green }}>
            <FileText className="w-3.5 h-3.5" />
            直接粘贴文本内容
          </div>
          <textarea
            className={`flex-1 min-h-[120px] border rounded-xl px-3 py-2 resize-none outline-none ${ty.input}`}
            style={{ borderColor: t.border, backgroundColor: t.bg, color: t.text }}
            placeholder="在此粘贴笔记、会议纪要、代码片段…"
            value={imp.textContent}
            onChange={(e) => imp.setTextContent(e.target.value)}
          />
        </div>
      );
    }

    if (imp.tab === "URL 导入") {
      return (
        <div className="space-y-2">
          <div className={`flex items-center gap-1.5 ${ty.label}`} style={{ color: t.green }}>
            <Link2 className="w-3.5 h-3.5" />
            单条网页 / 文档链接
          </div>
          <input
            className={`w-full border rounded-xl px-3 py-2 outline-none ${ty.input}`}
            style={{ borderColor: t.border, backgroundColor: t.bg, color: t.text }}
            placeholder="https://example.com/article"
            value={imp.urlValue}
            onChange={(e) => imp.setUrlValue(e.target.value)}
          />
          <p className={ty.caption} style={{ color: t.textMuted }}>
            将 URL 标记写入记忆；正文抓取由 Runtime 后续处理。
          </p>
        </div>
      );
    }

    return (
      <div className="space-y-3">
        <div className={`flex items-center gap-1.5 ${ty.label}`} style={{ color: t.green }}>
          <FileStack className="w-3.5 h-3.5" />
          多文件 + 多 URL 混合导入
        </div>
        <label
          className={`flex items-center justify-center gap-2 p-4 rounded-xl border border-dashed cursor-pointer ${
            !imp.canImport && !imp.isDemo ? "opacity-60" : ""
          }`}
          style={{ borderColor: `${t.green}44`, backgroundColor: t.greenSoft }}
        >
          <UploadCloud className="w-5 h-5" style={{ color: t.green }} />
          <span className={ty.body} style={{ color: t.textMuted }}>
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
          className={`w-full min-h-[88px] border rounded-xl px-3 py-2 resize-none outline-none ${ty.input}`}
          style={{ borderColor: t.border, backgroundColor: t.bg, color: t.text }}
          placeholder={"每行一个 URL\nhttps://a.com\nhttps://b.com/doc"}
          value={imp.batchUrls}
          onChange={(e) => imp.setBatchUrls(e.target.value)}
        />
      </div>
    );
  };

  const episodicHint =
    imp.layer === "episodic" && embeddingStatus ? (
      <p className={`${ty.caption} flex items-center gap-1 flex-wrap`} style={{ color: t.textLight }}>
        <span>经历向量</span>
        <EmbeddingModeBadge status={embeddingStatus} compact />
        <span>· 导入时写入 · 检索时查询 · 保存不触发反思</span>
      </p>
    ) : null;

  const renderTargetSelectors = () => (
    <div className="grid grid-cols-1 gap-2 text-xs shrink-0">
      <label className="flex flex-col gap-1">
        <span className="inline-flex items-center gap-1" style={{ color: t.textMuted }}>
          目标类型
          {imp.layer === "episodic" && <EmbeddingModeBadge status={embeddingStatus} compact />}
        </span>
        <select
          className="border rounded px-2 py-1.5"
          style={{ borderColor: t.border, backgroundColor: t.bg, color: t.text }}
          value={imp.layer}
          onChange={(e) => imp.setLayer(e.target.value)}
        >
          {LAYER_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </label>
      {episodicHint}
      <label className="flex flex-col gap-1">
        <span style={{ color: t.textMuted }}>关联目标</span>
        <select
          className="border rounded px-2 py-1.5"
          style={{ borderColor: t.border, backgroundColor: t.bg, color: t.text }}
          value={imp.activeGoal}
          onChange={(e) => imp.setRelatedGoal(e.target.value)}
        >
          {imp.goalSelectOptions.map((g) => (
            <option key={g.value} value={g.value}>
              {g.label}
            </option>
          ))}
        </select>
      </label>
    </div>
  );

  const renderActionFooter = () => (
    <>
      {renderTargetSelectors()}
      {imp.files.length > 0 && (
        <ul className={`${ty.mono} space-y-1 shrink-0 max-h-16 overflow-y-auto`} style={{ color: t.textMuted }}>
          {imp.files.slice(-6).map((f, i) => (
            <li key={`${f.name}-${i}`}>✓ {f.name}</li>
          ))}
          {imp.files.length > 6 && <li>…共 {imp.files.length} 项</li>}
        </ul>
      )}
      {imp.statusHint && (
        <p className={`${ty.caption} shrink-0`} style={{ color: t.orange }}>
          {imp.statusHint}
        </p>
      )}
      {imp.importNote && (
        <p className={`${ty.caption} shrink-0`} style={{ color: t.textMuted }}>
          {imp.importNote}
        </p>
      )}
      <button
        type="button"
        className={`w-full py-2.5 rounded-lg shrink-0 ${ty.btn}`}
        style={{ backgroundColor: t.green }}
        disabled={imp.importing || (!imp.canImport && !imp.isDemo)}
        onClick={() => void imp.startImport()}
      >
        {imp.importing
          ? "导入中…"
          : imp.tab === "文档导入"
            ? "确认文档导入"
            : imp.tab === "批量导入"
              ? "开始批量导入"
              : "开始导入"}
      </button>
    </>
  );

  const tabHeader = (
    <div className="p-3 border-b shrink-0" style={{ borderColor: t.border }}>
      {!isCognitive && (
        <p className="text-sm font-semibold mb-2" style={{ color: t.green }}>
          Upload 导入面板
        </p>
      )}
      <div className="flex gap-1 flex-wrap">
        {imp.visibleTabs.map((label) => (
          <button
            key={label}
            type="button"
            className={`px-2.5 py-1 rounded-md transition ${ty.tab}`}
            style={{
              backgroundColor: imp.tab === label ? t.greenSoft : "transparent",
              color: imp.tab === label ? t.green : t.textMuted,
              fontWeight: imp.tab === label ? 600 : 400,
              border: imp.tab === label ? `1px solid ${t.green}44` : "1px solid transparent",
            }}
            onClick={() => imp.selectTab(label as ImportTab)}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );

  return (
    <div
      className={`flex flex-col ${panelHeightClass} ${isCognitive ? "" : "shadow-sm"}`}
      style={{
        backgroundColor: t.surface,
        borderColor: t.border,
        borderTopWidth: isCognitive ? 1 : 3,
        borderTopColor: isCognitive ? t.border : t.green,
        opacity: isCognitive ? 0.85 : 1,
      }}
    >
      {tabHeader}

      {variant === "overview" ? (
        <>
          <div className={scrollAreaClass}>{renderTabBody()}</div>
          <div
            className="shrink-0 border-t p-4 flex flex-col gap-2"
            style={{ borderColor: t.border, backgroundColor: t.surface }}
          >
            {renderActionFooter()}
          </div>
        </>
      ) : (
        <div className={`${scrollAreaClass} flex flex-col gap-3 p-4`}>
          {renderTabBody()}
          {renderActionFooter()}
        </div>
      )}
    </div>
  );
}
