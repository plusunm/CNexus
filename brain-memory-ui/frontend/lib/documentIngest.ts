import { brainApi, type IngestDocumentResult } from "@/lib/api";
import { DOCUMENT_ACCEPT } from "@/lib/memoryWriteReady";

export { DOCUMENT_ACCEPT };

const TEXT_EXT = /\.(txt|md|markdown)$/i;

export type IngestFileOptions = {
  layer?: string;
  importance?: number;
  cognize?: boolean;
  goal?: string;
};

/** Demo/local text read for plain-text files only. */
export async function readLocalTextFile(file: File, maxChars = 4000): Promise<string> {
  if (!TEXT_EXT.test(file.name)) {
    throw new Error("演示模式仅支持 TXT / Markdown 文件");
  }
  const text = await file.text().catch(() => "");
  const trimmed = text.trim().slice(0, maxChars);
  if (!trimmed) throw new Error("文件无有效文本");
  return trimmed;
}

export async function ingestDocumentFile(
  file: File,
  opts: IngestFileOptions = {},
): Promise<IngestDocumentResult> {
  return brainApi.ingestDocument(file, {
    layer: opts.layer ?? "episodic",
    importance: opts.importance ?? 0.7,
    cognize: opts.cognize ?? true,
    goal: opts.goal,
  });
}

export function formatIngestKeywords(keywords: string[] | undefined): string | null {
  if (!keywords?.length) return null;
  return keywords.slice(0, 8).join(" · ");
}
