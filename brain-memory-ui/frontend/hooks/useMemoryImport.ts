"use client";

import { useMemo, useRef, useState } from "react";
import { brainApi } from "@/lib/api";
import { useMindOverview, useMindStore } from "@/cnexus-kernel";
import { loadDingTalkConfig, sendDingTalkTest } from "@/lib/floatIntegrations";
import {
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

export const IMPORT_TABS = ["文档导入", "文本导入", "URL 导入", "批量导入"] as const;
export type ImportTab = (typeof IMPORT_TABS)[number];

export const LAYER_OPTIONS = [
  { value: "episodic", label: "经历 (Episodic)" },
  { value: "goal", label: "目标 (Goal)" },
  { value: "identity", label: "身份 (Identity)" },
] as const;

export const FLOAT_LAYER_OPTIONS = [
  { value: "episodic", label: "经历" },
  { value: "goal", label: "目标" },
  { value: "identity", label: "身份" },
] as const;

type Options = {
  /** Float: pick files first, import on confirm */
  deferFileCapture?: boolean;
  excludeDocImport?: boolean;
  /** Open overview debugger after successful import (main window only). */
  navigateAfterImport?: boolean;
};

export function useMemoryImport({
  deferFileCapture = false,
  excludeDocImport = false,
  navigateAfterImport = true,
}: Options = {}) {
  const { overview, isDemo, isWarming, isLive, isFallback, canWriteMemory } = useMindOverview();
  const afterMemoryCapture = useMindStore((s) => s.afterMemoryCapture);
  const { navigateDebuggerAfterImport } = useShellNavigation();

  const writeGate = useMemo(
    () => ({
      isDemo,
      isWarming,
      isFallback,
      canWriteMemory,
      isLive,
    }),
    [isDemo, isWarming, isFallback, canWriteMemory, isLive],
  );
  const canImport = canWriteMemory;
  const statusHint = memoryWriteStatusHint(writeGate);

  const visibleTabs = useMemo(
    () => (excludeDocImport ? IMPORT_TABS.filter((x) => x !== "文档导入") : [...IMPORT_TABS]),
    [excludeDocImport],
  );

  const [tab, setTab] = useState<ImportTab>(() =>
    excludeDocImport ? "文本导入" : "文档导入",
  );
  const [files, setFiles] = useState<File[]>([]);
  const [textContent, setTextContent] = useState("");
  const [urlValue, setUrlValue] = useState("");
  const [batchUrls, setBatchUrls] = useState("");
  const [layer, setLayer] = useState("episodic");
  const [relatedGoal, setRelatedGoal] = useState("");
  const [importNote, setImportNote] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);

  const docInputRef = useRef<HTMLInputElement>(null);
  const batchInputRef = useRef<HTMLInputElement>(null);

  const goalOptions = useMemo(() => {
    const fromItems = overview.memory_items
      .filter((i) => i.tag === "goal")
      .map((i) => i.title);
    const primary = overview.cards.goal.title;
    return [...new Set([primary, ...fromItems].filter((x): x is string => Boolean(x)))];
  }, [overview]);

  const activeGoal = relatedGoal || goalOptions[0] || "";

  const goalSelectOptions =
    goalOptions.length > 0
      ? goalOptions.map((g) => ({ value: g, label: g }))
      : [{ value: "__none__", label: "（暂无关联目标）" }];

  const wrapPayload = (text: string) => {
    const body = text.trim().slice(0, 4000);
    return activeGoal ? `[goal:${activeGoal}] ${body}` : body;
  };

  const notifyDingTalk = async (summary: string) => {
    const cfg = loadDingTalkConfig();
    if (!cfg.enabled || !cfg.notifyOnCapture || isDemo) return;
    try {
      await sendDingTalkTest(cfg, `CNexus 导入完成：${summary}`);
    } catch {
      /* optional notify */
    }
  };

  const finishImportSuccess = async (
    label: string,
    content: string,
    keywords?: string[],
    navigate = true,
  ) => {
    await afterMemoryCapture({ content, layer, label, keywords });
    if (navigate) navigateDebuggerAfterImport();
  };

  const guardWriteReady = async (): Promise<boolean> => {
    const result = await ensureMemoryWriteReady(writeGate);
    if (!result.ok) setImportNote(result.hint ?? statusHint ?? "Runtime 未连接，无法导入");
    return result.ok;
  };

  const captureText = async (text: string, label: string): Promise<boolean> => {
    if (!text.trim()) return false;
    const payload = wrapPayload(text);
    if (isDemo) {
      setFiles((f) => [...f, new File([text], label)]);
      await finishImportSuccess(label, payload, undefined, false);
      return true;
    }
    if (!(await guardWriteReady())) return false;
    try {
      const result = await brainApi.capture(payload, layer, "user", 0.7, true);
      setFiles((f) => [...f, new File([text], label)]);
      const traits = Array.isArray(result.cognition?.traits)
        ? (result.cognition?.traits as string[])
        : undefined;
      await finishImportSuccess(label, payload, traits, navigateAfterImport);
      return true;
    } catch (err) {
      setImportNote(formatImportError(err, "导入失败 — Runtime 未连接或拒绝写入"));
      return false;
    }
  };

  const captureFiles = async (picked: File[]): Promise<{ ok: number; fail: number }> => {
    let ok = 0;
    let fail = 0;
    let lastKeywords: string[] | undefined;
    if (!isDemo && !(await guardWriteReady())) return { ok: 0, fail: picked.length };

    for (const file of picked) {
      try {
        if (isDemo) {
          const text = await readLocalTextFile(file);
          const payload = wrapPayload(text);
          await afterMemoryCapture({ content: payload, layer, label: file.name });
          ok += 1;
          continue;
        }
        const ingested = await ingestDocumentFile(file, {
          layer,
          goal: activeGoal || undefined,
          cognize: true,
        });
        lastKeywords = ingested.keywords;
        await afterMemoryCapture({
          content: ingested.preview,
          layer,
          label: file.name,
          keywords: ingested.keywords,
        });
        ok += 1;
      } catch (err) {
        fail += 1;
        if (fail === 1) {
          setImportNote(formatImportError(err, "部分文件导入失败"));
        }
      }
    }
    if (ok > 0 && navigateAfterImport) navigateDebuggerAfterImport();
    if (ok > 0 && lastKeywords?.length) {
      const hint = formatIngestKeywords(lastKeywords);
      if (hint) setImportNote((prev) => (prev ? `${prev} · 关键词：${hint}` : `关键词：${hint}`));
    }
    return { ok, fail };
  };

  const onFiles = async (list: FileList | null, input?: HTMLInputElement | null) => {
    if (!list) return;
    const picked = Array.from(list);
    setFiles((f) => [...f, ...picked]);
    if (input) input.value = "";

    if (deferFileCapture) {
      setImportNote(`已选 ${picked.length} 个文件`);
      return;
    }

    if (!isDemo && !canImport) {
      setImportNote(statusHint ?? "Runtime 未连接，无法导入");
      return;
    }

    const { ok, fail } = await captureFiles(picked);
    if (ok > 0) {
      setImportNote(
        fail > 0
          ? `已导入 ${ok} 个，${fail} 个失败`
          : `已导入 ${ok} 个文件`,
      );
    } else if (fail > 0) {
      setImportNote("导入失败 — 请检查 Runtime 连接");
    }
  };

  const clearFiles = () => {
    setFiles([]);
    if (docInputRef.current) docInputRef.current.value = "";
    if (batchInputRef.current) batchInputRef.current.value = "";
  };

  const selectTab = (next: ImportTab) => {
    setTab(next);
    setImportNote(null);
  };

  const startImport = async () => {
    setImportNote(null);
    if (!isDemo && !canImport && !(await guardWriteReady())) return;

    setImporting(true);
    let ok = 0;

    try {
      if (tab === "文档导入") {
        if (files.length === 0) {
          setImportNote("请先选择文档");
          return;
        }
        const { ok: captured, fail } = await captureFiles([...files]);
        if (captured > 0) {
          await notifyDingTalk(`${captured} 个文档`);
          setImportNote(fail > 0 ? `已导入 ${captured} 个，${fail} 个失败` : `已导入 ${captured} 个文档`);
          clearFiles();
        }
        return;
      }

      if (tab === "文本导入") {
        if (!textContent.trim()) {
          setImportNote("请粘贴文本");
          return;
        }
        const success = await captureText(textContent, "pasted.txt");
        if (success) {
          await notifyDingTalk("文本片段");
          setTextContent("");
          setImportNote(
            navigateAfterImport ? "文本已导入 — 已跳转因果调试视图" : "文本已导入",
          );
        }
        return;
      }

      if (tab === "URL 导入") {
        const url = urlValue.trim();
        if (!url) {
          setImportNote("请填写链接");
          return;
        }
        const payload = `[url:${url}] ${url}`;
        const success = await captureText(payload, "url-import.txt");
        if (success) {
          await notifyDingTalk(url);
          setUrlValue("");
          setImportNote(
            navigateAfterImport ? "链接已写入记忆 — 已跳转因果调试视图" : "链接已写入记忆",
          );
        }
        return;
      }

      const urlLines = batchUrls
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter(Boolean);
      if (urlLines.length === 0 && files.length === 0) {
        setImportNote("请添加文件或 URL 列表");
        return;
      }
      for (const url of urlLines) {
        if (await captureText(`[url:${url}] ${url}`, `batch-url-${ok}.txt`)) ok += 1;
      }
      if (files.length > 0) {
        const { ok: fileOk } = await captureFiles([...files]);
        ok += fileOk;
        clearFiles();
      }
      await notifyDingTalk(`批量 ${ok} 条`);
      setBatchUrls("");
      setImportNote(`批量完成：${ok} 条`);
    } finally {
      setImporting(false);
    }
  };

  const importButtonLabel =
    tab === "文档导入"
      ? files.length > 0
        ? `导入 ${files.length} 个文档`
        : "选择并导入文档"
      : tab === "批量导入"
        ? "开始批量导入"
        : "写入记忆";

  return {
    isDemo,
    canImport,
    statusHint,
    visibleTabs,
    tab,
    selectTab,
    files,
    textContent,
    setTextContent,
    urlValue,
    setUrlValue,
    batchUrls,
    setBatchUrls,
    layer,
    setLayer,
    relatedGoal,
    setRelatedGoal,
    importNote,
    importing,
    docInputRef,
    batchInputRef,
    goalSelectOptions,
    activeGoal,
    onFiles,
    clearFiles,
    startImport,
    importButtonLabel,
  };
}
