"use client";

import { useRef, useState } from "react";
import { FileStack, Loader2, UploadCloud } from "lucide-react";
import { useMindOverview, useMindStore } from "@/cnexus-kernel";
import { useMindTheme } from "../MindUiProvider";
import {
  DOCUMENT_ACCEPT,
  formatIngestKeywords,
  ingestDocumentFile,
  readLocalTextFile,
} from "@/lib/documentIngest";
import {
  ensureMemoryWriteReady,
  formatImportError,
  memoryWriteStatusHint,
} from "@/lib/memoryWriteReady";
import { useShellNavigation } from "@/lib/shellNavigation";

type Props = {
  onImported?: (count: number, keywords?: string[]) => void;
  compact?: boolean;
};

/** 批量文档上传 — 写入长期记忆 */
export function HomeDocumentUpload({ onImported, compact }: Props) {
  const t = useMindTheme();
  const { isDemo, isWarming, isFallback, canWriteMemory, isLive } = useMindOverview();
  const afterMemoryCapture = useMindStore((s) => s.afterMemoryCapture);
  const { navigateDebuggerAfterImport } = useShellNavigation();
  const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [layer, setLayer] = useState<"episodic" | "goal">("episodic");
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  const writeGate = { isDemo, isWarming, isFallback, canWriteMemory, isLive };
  const canImport = canWriteMemory;
  const statusHint = memoryWriteStatusHint(writeGate);

  const addFiles = (list: FileList | null) => {
    if (!list?.length) return;
    setFiles((prev) => [...prev, ...Array.from(list)]);
    setNote(null);
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const importAll = async () => {
    if (files.length === 0) {
      setNote("请先选择要上传的文档");
      return;
    }
    if (!isDemo) {
      const ready = await ensureMemoryWriteReady(writeGate);
      if (!ready.ok) {
        setNote(ready.hint ?? statusHint ?? "Runtime 未连接，无法上传");
        return;
      }
    }

    setBusy(true);
    setNote(null);
    let ok = 0;
    let lastKeywords: string[] | undefined;
    let lastError: string | null = null;

    for (const file of files) {
      try {
        if (isDemo) {
          const text = await readLocalTextFile(file);
          await afterMemoryCapture({ content: text, layer, label: file.name });
          ok += 1;
          continue;
        }
        const ingested = await ingestDocumentFile(file, { layer, cognize: true });
        lastKeywords = ingested.keywords;
        await afterMemoryCapture({
          content: ingested.preview,
          layer,
          label: file.name,
          keywords: ingested.keywords,
        });
        ok += 1;
      } catch (err) {
        lastError = formatImportError(err, "导入失败");
      }
    }

    setBusy(false);
    if (ok > 0) {
      setFiles([]);
      if (inputRef.current) inputRef.current.value = "";
      const keywordHint = formatIngestKeywords(lastKeywords);
      const base = `已成功导入 ${ok} 个文档到${layer === "goal" ? "目标" : "经历"}记忆`;
      setNote(keywordHint ? `${base} · 关键词：${keywordHint} · 已跳转因果链` : `${base} · 已跳转因果链`);
      navigateDebuggerAfterImport();
      onImported?.(ok, lastKeywords);
    } else {
      setNote(lastError ?? (isDemo ? "导入失败" : "导入失败 — 请确认 Runtime 已连接"));
    }
  };

  return (
    <section
      className={`rounded-2xl border ${compact ? "p-3 flex-1 flex flex-col min-h-0" : "p-4"}`}
      style={{ borderColor: t.border, backgroundColor: t.surface }}
    >
      <div className={`flex items-center justify-between gap-2 ${compact ? "mb-2" : "mb-3"}`}>
        <div className="flex items-center gap-2 min-w-0">
          <FileStack className="w-4 h-4 shrink-0" style={{ color: t.green }} />
          <h3 className="text-sm font-semibold truncate" style={{ color: t.text }}>
            批量上传文档
          </h3>
        </div>
        <div className="flex gap-1 p-0.5 rounded-lg text-[10px] shrink-0" style={{ backgroundColor: t.chatBg }}>
          {(
            [
              { id: "episodic" as const, label: "经历记忆" },
              { id: "goal" as const, label: "目标记忆" },
            ] as const
          ).map((opt) => (
            <button
              key={opt.id}
              type="button"
              onClick={() => setLayer(opt.id)}
              className="px-2.5 py-1 rounded-md font-medium"
              style={{
                backgroundColor: layer === opt.id ? t.greenSoft : "transparent",
                color: layer === opt.id ? t.green : t.textMuted,
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {statusHint && (
        <p className="text-[11px] mb-2 leading-snug" style={{ color: t.orange }}>
          {statusHint}
        </p>
      )}

      <div className={compact ? "flex flex-col gap-2 flex-1 min-h-0" : "grid grid-cols-1 md:grid-cols-[1fr_auto] gap-3"}>
        <label
          className={`flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed transition-colors ${
            compact ? "p-4 flex-1 min-h-[100px]" : "p-5"
          } ${
            !canImport && !isDemo
              ? "opacity-55 cursor-not-allowed pointer-events-none"
              : "cursor-pointer"
          }`}
          style={{
            borderColor: dragging ? t.green : `${t.green}55`,
            backgroundColor: dragging ? t.greenSoft : t.chatBg,
          }}
          onDragEnter={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            addFiles(e.dataTransfer.files);
          }}
        >
          <UploadCloud className={compact ? "w-6 h-6" : "w-7 h-7"} style={{ color: t.green }} />
          <span className="text-[11px] text-center leading-snug px-2" style={{ color: t.textMuted }}>
            {compact ? "拖拽或点击选择多个文件" : "拖拽 PDF / Word / TXT / Markdown，或点击选择多个文件"}
          </span>
          <input
            ref={inputRef}
            type="file"
            multiple
            accept={DOCUMENT_ACCEPT}
            className="hidden"
            onChange={(e) => addFiles(e.target.files)}
          />
        </label>

        <div className={compact ? "flex gap-2" : "flex flex-col gap-2 min-w-[140px]"}>
          <button
            type="button"
            disabled={busy || files.length === 0 || (!canImport && !isDemo)}
            onClick={() => void importAll()}
            className={`rounded-xl text-sm font-medium disabled:opacity-40 flex items-center justify-center gap-2 ${
              compact ? "flex-1 py-2" : "py-2.5 px-4"
            }`}
            style={{ backgroundColor: t.green, color: "#fff" }}
          >
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            开始导入 {files.length > 0 ? `(${files.length})` : ""}
          </button>
          {files.length > 0 && (
            <button
              type="button"
              onClick={() => {
                setFiles([]);
                if (inputRef.current) inputRef.current.value = "";
              }}
              className={`rounded-lg text-xs border ${compact ? "px-3 py-2" : "py-2"}`}
              style={{ borderColor: t.border, color: t.textMuted }}
            >
              清空
            </button>
          )}
        </div>
      </div>

      {files.length > 0 && (
        <ul className={`mt-2 overflow-auto space-y-1 ${compact ? "max-h-[72px]" : "max-h-[120px]"}`}>
          {files.map((file, i) => (
            <li
              key={`${file.name}-${i}`}
              className="flex items-center justify-between gap-2 text-xs px-3 py-1.5 rounded-lg"
              style={{ backgroundColor: t.chatBg, color: t.textMuted }}
            >
              <span className="truncate">{file.name}</span>
              <button type="button" onClick={() => removeFile(i)} style={{ color: t.red }}>
                移除
              </button>
            </li>
          ))}
        </ul>
      )}

      {note && (
        <p className="mt-2 text-xs" style={{ color: note.includes("成功") ? t.green : t.orange }}>
          {note}
        </p>
      )}
    </section>
  );
}
