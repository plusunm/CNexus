/** Local share snippet — no network; safe for float/desktop offline use. */

export type ChatSharePayload = {
  role: "user" | "assistant";
  text: string;
  createdAt: number;
};

export function buildChatSharePayload(role: "user" | "assistant", text: string): ChatSharePayload {
  return {
    role,
    text: text.trim().slice(0, 4000),
    createdAt: Date.now(),
  };
}

export function buildChatShareLink(payload: ChatSharePayload): string {
  const json = JSON.stringify(payload);
  const encoded =
    typeof window !== "undefined"
      ? btoa(unescape(encodeURIComponent(json)))
      : json;
  return `cnexus://chat/share?v=1&p=${encodeURIComponent(encoded)}`;
}

export function formatChatShareText(payload: ChatSharePayload): string {
  const who = payload.role === "user" ? "我" : "CNexus";
  return `[CNexus 对话分享]\n${who}：\n${payload.text}`;
}

export async function copyChatShare(payload: ChatSharePayload): Promise<void> {
  const link = buildChatShareLink(payload);
  const body = `${formatChatShareText(payload)}\n\n链接：${link}`;
  if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(body);
    return;
  }
  throw new Error("clipboard unavailable");
}
