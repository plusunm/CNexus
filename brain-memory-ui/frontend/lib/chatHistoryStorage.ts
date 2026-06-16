export type StoredChatMessage = {
  role: "user" | "assistant";
  text: string;
  meta?: string;
};

const STORAGE_KEY = "cnexus-chat-messages-v1";
const MAX_MESSAGES = 200;

function isValidMessage(value: unknown): value is StoredChatMessage {
  if (!value || typeof value !== "object") return false;
  const row = value as Record<string, unknown>;
  const roleOk = row.role === "user" || row.role === "assistant";
  return roleOk && typeof row.text === "string";
}

export function loadChatMessages(): StoredChatMessage[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isValidMessage).slice(-MAX_MESSAGES);
  } catch {
    return [];
  }
}

export function saveChatMessages(messages: StoredChatMessage[]): void {
  if (typeof window === "undefined") return;
  try {
    const trimmed = messages.slice(-MAX_MESSAGES);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
  } catch {
    /* ignore quota / private mode */
  }
}

export function clearChatMessages(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(STORAGE_KEY);
}
