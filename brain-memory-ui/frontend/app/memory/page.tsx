"use client";

import { useState } from "react";
import { brainApi } from "@/lib/api";

const LAYERS = ["episodic", "goal", "belief", "identity", "semantic", "narrative"];

export default function MemoryPage() {
  const [query, setQuery] = useState("");
  const [recallResult, setRecallResult] = useState("");
  const [captureContent, setCaptureContent] = useState("");
  const [layer, setLayer] = useState("episodic");

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <header>
        <h1 className="text-2xl font-bold">记忆管理</h1>
        <p className="text-gray-400 text-sm">手动召回 / 写入 Brain-Memory 分层存储</p>
      </header>

      <div className="card space-y-3">
        <h2 className="font-semibold">召回 Recall</h2>
        <input
          className="input"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="查询：我的长期目标是什么？"
        />
        <button
          className="btn"
          onClick={() => brainApi.recall(query).then((r) => setRecallResult(r.context))}
        >
          召回
        </button>
        {recallResult && (
          <pre className="text-xs bg-bg p-4 rounded-lg overflow-auto max-h-96 whitespace-pre-wrap border border-border">
            {recallResult}
          </pre>
        )}
      </div>

      <div className="card space-y-3">
        <h2 className="font-semibold">写入 Capture</h2>
        <select className="input" value={layer} onChange={(e) => setLayer(e.target.value)}>
          {LAYERS.map((l) => (
            <option key={l} value={l}>
              {l}
            </option>
          ))}
        </select>
        <textarea
          className="input"
          rows={4}
          value={captureContent}
          onChange={(e) => setCaptureContent(e.target.value)}
          placeholder="写入一条长期记忆…"
        />
        <button
          className="btn"
          onClick={() =>
            brainApi.capture(captureContent, layer).then((r) => alert(`已写入: ${r.memory_id}`))
          }
        >
          写入记忆
        </button>
      </div>
    </div>
  );
}
