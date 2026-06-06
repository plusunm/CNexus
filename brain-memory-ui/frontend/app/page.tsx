"use client";

import { useAppStore } from "@/lib/store";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { useEffect, useState } from "react";
import { brainApi } from "@/lib/api";

export default function DashboardPage() {
  const { runtimeState } = useAppStore();
  const [history, setHistory] = useState<{ t: string; stability: number }[]>([]);

  useEffect(() => {
    if (!runtimeState) return;
    setHistory((h) => [
      ...h.slice(-29),
      {
        t: new Date(runtimeState.timestamp).toLocaleTimeString(),
        stability: runtimeState.stability_metrics.overall_stability_score ?? 0.85,
      },
    ]);
  }, [runtimeState]);

  const metrics = runtimeState?.stability_metrics ?? {};

  return (
    <div className="p-6 space-y-6">
      <header>
        <h1 className="text-2xl font-bold">稳定性仪表盘</h1>
        <p className="text-gray-400 text-sm mt-1">实时监控认知状态与人格连续性</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          ["整体稳定性", metrics.overall_stability_score, "overall"],
          ["叙事连贯性", runtimeState?.narrative.coherence, "narrative"],
          ["身份稳定性", metrics.identity_stability, "identity"],
          ["Working Memory", runtimeState?.working_memory_count, "wm"],
        ].map(([label, val, key]) => (
          <div key={key as string} className="card">
            <div className="text-xs text-gray-400">{label as string}</div>
            <div className="text-2xl font-bold mt-1">
              {typeof val === "number" ? (key === "wm" ? val : val.toFixed(3)) : "—"}
            </div>
          </div>
        ))}
      </div>

      <div className="card h-72">
        <h2 className="font-semibold mb-4">稳定性趋势</h2>
        <ResponsiveContainer width="100%" height="85%">
          <LineChart data={history}>
            <CartesianGrid stroke="#2a3144" />
            <XAxis dataKey="t" stroke="#8b95a8" tick={{ fontSize: 11 }} />
            <YAxis domain={[0, 1]} stroke="#8b95a8" tick={{ fontSize: 11 }} />
            <Tooltip contentStyle={{ background: "#171b26", border: "1px solid #2a3144" }} />
            <Line type="monotone" dataKey="stability" stroke="#6c8cff" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card">
          <h2 className="font-semibold mb-2">叙事自我</h2>
          <p className="text-sm text-gray-300 leading-relaxed">
            {runtimeState?.narrative.summary ?? "等待 Runtime 连接…"}
          </p>
        </div>
        <div className="card">
          <h2 className="font-semibold mb-2">活跃信念</h2>
          <ul className="space-y-2 text-sm">
            {Object.entries(runtimeState?.beliefs ?? {}).map(([k, v]) => (
              <li key={k} className="flex justify-between gap-2 border-b border-border pb-2">
                <span className="text-gray-300">{v.content.slice(0, 80)}</span>
                <span className="text-accent2 shrink-0">{v.confidence.toFixed(2)}</span>
              </li>
            ))}
            {!Object.keys(runtimeState?.beliefs ?? {}).length && (
              <li className="text-gray-500">暂无信念记录</li>
            )}
          </ul>
        </div>
      </div>

      <button
        className="btn"
        onClick={() => brainApi.governance().then(() => alert("治理周期已完成"))}
      >
        运行稳定性治理
      </button>
    </div>
  );
}
