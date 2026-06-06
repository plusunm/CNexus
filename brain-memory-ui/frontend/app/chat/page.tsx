"use client";

import { useState } from "react";
import { brainApi } from "@/lib/api";
import { useAppStore } from "@/lib/store";

export default function ChatPage() {
  const { models, selectedModelId, setSelectedModel } = useAppStore();
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [input, setInput] = useState("");
  const [useMemory, setUseMemory] = useState(true);
  const [loading, setLoading] = useState(false);

  async function send() {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setInput("");
    setMessages((m) => [...m, { role: "user", content: userMsg }]);
    setLoading(true);
    try {
      const res = await brainApi.chat(userMsg, selectedModelId || undefined, useMemory);
      setMessages((m) => [...m, { role: "assistant", content: res.reply }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "system", content: String(e) }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-screen">
      <header className="p-6 border-b border-border">
        <h1 className="text-xl font-bold">Agent 对话</h1>
        <div className="flex gap-4 mt-3 items-center flex-wrap">
          <select
            className="input w-auto"
            value={selectedModelId}
            onChange={(e) => setSelectedModel(e.target.value)}
          >
            {models.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name} ({m.model})
              </option>
            ))}
          </select>
          <label className="text-sm flex items-center gap-2">
            <input type="checkbox" checked={useMemory} onChange={(e) => setUseMemory(e.target.checked)} />
            启用 Brain-Memory 召回
          </label>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`max-w-3xl p-4 rounded-xl text-sm whitespace-pre-wrap ${
              m.role === "user"
                ? "ml-auto bg-accent/20 border border-accent/30"
                : m.role === "assistant"
                ? "bg-surface border border-border"
                : "text-red-400 text-center"
            }`}
          >
            {m.content}
          </div>
        ))}
      </div>

      <div className="p-4 border-t border-border flex gap-3">
        <textarea
          className="input flex-1 resize-none"
          rows={2}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          placeholder="输入消息…"
        />
        <button className="btn self-end" disabled={loading} onClick={send}>
          {loading ? "…" : "发送"}
        </button>
      </div>
    </div>
  );
}
