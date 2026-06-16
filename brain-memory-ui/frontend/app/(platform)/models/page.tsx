"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getEdition, getEditionProfile, useMindStore } from "@/cnexus-kernel";
import { brainApi } from "@/lib/api";
import { useState } from "react";

export default function ModelsPage() {
  const router = useRouter();
  const profile = getEditionProfile(getEdition());
  const { models, refreshModels } = useMindStore();
  const [form, setForm] = useState({
    name: "",
    provider: "openai_compatible",
    base_url: "https://api.deepseek.com/v1",
    model: "deepseek-chat",
    api_key: "",
  });

  useEffect(() => {
    if (!profile.modelsAdmin) {
      router.replace("/shell?layout=overview");
    }
  }, [profile.modelsAdmin, router]);

  if (!profile.modelsAdmin) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-400 text-sm">
        模型管理仅企业版可用…
      </div>
    );
  }

  async function addModel(e: React.FormEvent) {
    e.preventDefault();
    await brainApi.createModel(form);
    setForm({ ...form, name: "", api_key: "" });
    await refreshModels();
  }

  return (
    <div className="p-6 space-y-6">
      <header>
        <h1 className="text-2xl font-bold">模型配置</h1>
        <p className="text-gray-400 text-sm">企业版 · 管理 LLM 提供商与 API Key</p>
      </header>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="card space-y-3">
          <h2 className="font-semibold">已配置</h2>
          {models.map((m) => (
            <div key={m.id} className="flex justify-between items-start p-3 bg-bg rounded-lg border border-border">
              <div>
                <div className="font-medium text-sm">
                  {m.name} {m.is_default && "★"}
                </div>
                <div className="text-xs text-gray-400 mt-1">
                  {m.provider} · {m.model}
                  <br />
                  Key: {m.api_key_set ? "已设置" : "未设置"}
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  className="btn-ghost text-xs text-red-400"
                  onClick={() => brainApi.deleteModel(m.id).then(refreshModels)}
                >
                  删除
                </button>
              </div>
            </div>
          ))}
        </div>

        <form className="card space-y-3" onSubmit={addModel}>
          <h2 className="font-semibold">添加模型</h2>
          {(["name", "base_url", "model", "api_key"] as const).map((f) => (
            <input
              key={f}
              className="input"
              placeholder={f}
              type={f === "api_key" ? "password" : "text"}
              value={form[f]}
              onChange={(e) => setForm({ ...form, [f]: e.target.value })}
              required={f !== "api_key"}
            />
          ))}
          <select
            className="input"
            value={form.provider}
            onChange={(e) => setForm({ ...form, provider: e.target.value })}
          >
            <option value="ollama">Ollama</option>
            <option value="openai">OpenAI</option>
            <option value="openai_compatible">OpenAI 兼容</option>
          </select>
          <button className="btn" type="submit">
            保存
          </button>
        </form>
      </div>
    </div>
  );
}
