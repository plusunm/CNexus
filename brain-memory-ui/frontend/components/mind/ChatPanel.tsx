"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, Send } from "lucide-react";
import { brainApi, getDefaultFullCognitiveLoop } from "@/lib/api";
import { buildChatSharePayload } from "@/lib/chatShare";
import {
  loadChatMessages,
  saveChatMessages,
  clearChatMessages,
  type StoredChatMessage,
} from "@/lib/chatHistoryStorage";
import { useMindStore } from "@/cnexus-kernel";
import { useMindOverview, useMindConnection } from "@/cnexus-kernel";
import { ChatMessageMenu } from "./ChatMessageMenu";
import { ChatShareDialog } from "./ChatShareDialog";
import { ChatOutboundAuthorizationDialog, type ChatOutboundPreview } from "./ChatOutboundAuthorizationDialog";
import { OllamaControlButton } from "./OllamaControlButton";
import { ChatModelSelect } from "./ChatModelSelect";
import { floatTy } from "@/lib/floatTypography";
import { useMindTheme } from "./MindUiProvider";
import { useRuntimeInteract } from "@/hooks/useRuntimeInteract";

type Msg = StoredChatMessage;

type PanelVariant = "overview" | "cognitive" | "float";

function formatChatError(detail: string): string {
  const lower = detail.toLowerCase();
  if (
    lower.includes("failed to fetch") ||
    lower.includes("networkerror") ||
    lower.includes("load failed")
  ) {
    return (
      "无法连接 Runtime（127.0.0.1:8000）。\n\n" +
      "请按顺序尝试：\n" +
      "1. 悬浮窗 →「连接服务」→「重新探测运行时」\n" +
      "2. 浏览器开发：确认 API 进程在运行（python -m api.main）\n" +
      "3. 桌面安装版：完全退出 CNexus 后重新打开"
    );
  }
  if (lower.includes("memory write blocked") || lower.includes("create_block must go through")) {
    return (
      "记忆写入被 Runtime 安全策略拦截（已修复，需重启 Runtime）。\n\n" +
      "请关闭并重新启动 CNexus Runtime（端口 8000），然后再试。\n" +
      "若重启后仍失败，请把完整错误信息反馈给开发者。"
    );
  }
  if (lower.includes("401") || lower.includes("unauthorized")) {
    return (
      "API Key 无效或已过期 (401 Unauthorized)\n\n" +
      "请到悬浮窗菜单 → 大模型 API，重新填写 DeepSeek Key 并保存。\n" +
      "若已保存仍失败，请在 platform.deepseek.com 确认 Key 有效且账户有余额。"
    );
  }
  if (lower.includes("abort") || lower.includes("timeout") || lower.includes("timed out")) {
    return "连接 Runtime 超时 — 请确认 CNexus Runtime 正在运行。";
  }
  if (
    lower.includes("service unavailable") ||
    lower.includes("503") ||
    lower.includes("still initializing") ||
    lower.includes("runtime warming") ||
    lower.includes("runtimenotready")
  ) {
    return (
      "Runtime 正在启动（首次启动约 1–2 分钟）。\n\n" +
      "请稍候再试，或：悬浮窗 → 连接服务 → 重新探测运行时。\n" +
      "HTTP 已在线但聊天需等内核就绪；DeepSeek Key 已保存则无需重复填写。"
    );
  }
  if (lower.includes("prepare_id") || lower.includes("授权预览已过期") || lower.includes("expired")) {
    return (
      "授权预览已过期。\n\n" +
      "请在输入框重新发送消息，生成新的授权预览后再点击「授权并发送」。\n" +
      "预览有效期通常为 5 分钟。"
    );
  }
  if (
    lower.includes("authoritydispatcher") ||
    lower.includes("takes 1 positional argument") ||
    lower.includes("takes 2 positional arguments") ||
    lower.includes("unexpected keyword argument")
  ) {
    return (
      `${detail.trim()}\n\n` +
      "这是 Runtime 内部调用协议错误（非模型或 Key 问题）。\n" +
      "请完全退出 CNexus 后重新打开，确保 API 进程加载最新代码；开发环境需重启 python -m api.main。"
    );
  }
  return `${detail}\n\n请检查：\n1. Runtime 是否在线\n2. 大模型 API 是否已保存 Key\n3. Base URL 应为 https://api.deepseek.com（无需 /v1）`;
}

export function ChatPanel({
  variant = "overview",
  autoFocusInput = false,
}: {
  variant?: PanelVariant;
  autoFocusInput?: boolean;
}) {
  const t = useMindTheme();
  const isCognitive = variant === "cognitive" || variant === "float";
  const isFloat = variant === "float";
  const selectedModelId = useMindStore((s) => s.selectedModelId);
  const models = useMindStore((s) => s.models);
  const { effectiveMode } = useMindConnection();
  const { overview, signals, isDemo, isLive } = useMindOverview();
  const { canChat, statusHint: runtimeGateHint } = useRuntimeInteract();
  const [messages, setMessages] = useState<Msg[]>(() => loadChatMessages());
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [menu, setMenu] = useState<{ x: number; y: number; index: number } | null>(null);
  const [shareIndex, setShareIndex] = useState<number | null>(null);
  const [authPreview, setAuthPreview] = useState<ChatOutboundPreview | null>(null);
  const [authLoading, setAuthLoading] = useState(false);
  const inputBlocked = loading || authLoading || (!isDemo && !canChat);
  const pendingModelIdRef = useRef<string | undefined>(undefined);
  const pendingUserTextRef = useRef("");
  const messagesScrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const prevEffectiveModeRef = useRef(effectiveMode);

  const ctx = overview.chat_context;

  const scrollMessagesToBottom = useCallback(() => {
    const el = messagesScrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, []);

  useEffect(() => {
    scrollMessagesToBottom();
  }, [messages, loading, scrollMessagesToBottom]);

  useEffect(() => {
    saveChatMessages(messages);
  }, [messages]);

  const closeMenus = useCallback(() => {
    setMenu(null);
    setShareIndex(null);
  }, []);

  /** 数据源切换时清空对话，避免 Demo/Runtime 上下文混用 */
  useEffect(() => {
    if (prevEffectiveModeRef.current === effectiveMode) return;
    prevEffectiveModeRef.current = effectiveMode;
    setMessages([]);
    setInput("");
    clearChatMessages();
    closeMenus();
  }, [effectiveMode, closeMenus]);

  const syncInputHeight = useCallback(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    const maxPx = isFloat ? 120 : 160;
    el.style.height = `${Math.min(el.scrollHeight, maxPx)}px`;
    el.style.overflowY = el.scrollHeight > maxPx ? "auto" : "hidden";
  }, [isFloat]);

  useEffect(() => {
    syncInputHeight();
  }, [input, syncInputHeight]);

  useEffect(() => {
    if (!isFloat || !autoFocusInput) return;
    const timer = window.setTimeout(() => inputRef.current?.focus(), 80);
    return () => window.clearTimeout(timer);
  }, [isFloat, autoFocusInput]);

  /** Strict: returns valid model_id or null. No silent fallback. */
  const resolveModelIdStrict = useCallback((): { valid: true; id: string } | { valid: false; reason: string } => {
    const selected = models.find((m) => m.id === selectedModelId);
    if (!selected || !selected.enabled) {
      return { valid: false, reason: "SELECTED_MODEL_DISABLED" };
    }
    if (selected.provider === "ollama") {
      return { valid: true, id: selected.id };
    }
    if (selected.api_key_set) {
      return { valid: true, id: selected.id };
    }
    return { valid: false, reason: "MODEL_NO_KEY" };
  }, [models, selectedModelId]);

  const appendAssistant = useCallback((text: string, meta?: string) => {
    setMessages((m) => [...m, { role: "assistant", text, meta }]);
  }, []);

  const fullCognitiveLoop = getDefaultFullCognitiveLoop();

  const finalizeAuthorizedReply = useCallback(
    async (
      prepareId: string,
      userText: string,
      modelId?: string,
      sendMode: "with_injection" | "user_only" = "with_injection",
    ) => {
      setAuthLoading(true);
      setLoading(true);
      try {
        const res = await brainApi.chatConfirm(prepareId, modelId, {
          authorized: true,
          sendMode,
          fullCognitiveLoop,
        });
        if (!res.reply?.trim()) {
          throw new Error("模型返回空回复");
        }
        setMessages((m) => [...m, { role: "user", text: userText }]);
        const capture = res.memory_capture;
        const govNotes = capture?.chat_governance_notes ?? [];
        const govWarning = govNotes
          .filter((n) => String(n.action ?? "").toUpperCase() === "BLOCK")
          .map((n) => `${String(n.stage ?? "governance")}: ${String(n.reason ?? "")}`)
          .join(" · ");
        const metaParts = [
          sendMode === "user_only" ? "跳过注入" : "已授权注入",
          capture?.intercepted ? "治理已拦截回复" : null,
          capture?.cognition_deferred ? "后台认知" : null,
          govWarning || null,
          res.coherence_score != null ? `coherence ${(res.coherence_score * 100).toFixed(0)}%` : null,
          res.active_intent ? `intent: ${res.active_intent}` : null,
          res.latency_ms != null ? `${Math.round(res.latency_ms)}ms` : null,
        ].filter(Boolean);
        appendAssistant(res.reply, metaParts.join(" · "));
      } catch (err) {
        const detail = err instanceof Error ? err.message : "未知错误";
        appendAssistant(`聊天失败：${formatChatError(detail)}`);
      } finally {
        setAuthLoading(false);
        setLoading(false);
        setAuthPreview(null);
      }
    },
    [appendAssistant, fullCognitiveLoop],
  );

  const cancelAuthorization = useCallback(async () => {
    if (authPreview?.prepareId) {
      try {
        await brainApi.chatCancel(authPreview.prepareId);
      } catch {
        /* ignore */
      }
    }
    setAuthPreview(null);
    setAuthLoading(false);
    setLoading(false);
  }, [authPreview]);

  const send = useCallback(async () => {
    if (!input.trim() || loading || authPreview || authLoading) return;
    if (!isDemo && !canChat) return;
    const text = input.trim();
    setLoading(true);
    if (isDemo) {
      setInput("");
      setMessages((m) => [
        ...m,
        { role: "user", text },
        {
          role: "assistant",
          text:
            `[Demo 模式 · 授权预览]\n\n【你的消息】\n${text}\n\n` +
            `【系统注入 · 记忆】\n(演示模式无 Runtime 注入)\n\n` +
            `【系统注入 · 治理】\n(演示模式无治理注入)\n\n` +
            `Demo 下不会真正调用模型。连接 Runtime 后可「授权并发送」或「仅发送我的消息」。`,
          meta: "demo · authorization preview",
        },
      ]);
      setLoading(false);
      return;
    }
    const modelRes = resolveModelIdStrict();
    if (!modelRes.valid) {
      appendAssistant(`⚠ 发送失败：未选择可用模型（${modelRes.reason}）\n请在下方选择一个已配置 API Key 或 Ollama 的模型。`);
      setLoading(false);
      return;
    }
    try {
      const modelId = modelRes.id;
      pendingModelIdRef.current = modelId;
      pendingUserTextRef.current = text;
      const prepared = await brainApi.chatPrepare(text, modelId, true, fullCognitiveLoop);
      const preview: ChatOutboundPreview = {
        prepareId: prepared.prepare_id,
        userMessage: prepared.user_message,
        memoryContext: prepared.memory_context,
        governanceInjection: prepared.governance_injection,
        systemPrompt: prepared.system_prompt,
        outboundPreview: prepared.outbound_preview,
        hasInjection: prepared.has_injection,
      };
      setAuthPreview(preview);
      setLoading(false);
    } catch (err) {
      const detail = err instanceof Error ? err.message : "未知错误";
      appendAssistant(`聊天失败：${formatChatError(detail)}`);
      setLoading(false);
    }
  }, [input, loading, authPreview, authLoading, isDemo, canChat, resolveModelIdStrict, appendAssistant, fullCognitiveLoop]);

  const openMessageMenu = useCallback((clientX: number, clientY: number, index: number) => {
    setShareIndex(null);
    setMenu({ x: clientX, y: clientY, index });
  }, []);

  const onMessagePointerDown = useCallback(
    (e: React.PointerEvent, index: number) => {
      if (e.button !== 2) return;
      e.preventDefault();
      e.stopPropagation();
      openMessageMenu(e.clientX, e.clientY, index);
    },
    [openMessageMenu],
  );

  const onMessageContextMenu = useCallback(
    (e: React.MouseEvent, index: number) => {
      e.preventDefault();
      e.stopPropagation();
      openMessageMenu(e.clientX, e.clientY, index);
    },
    [openMessageMenu],
  );

  const copyMessage = useCallback(
    async (index: number) => {
      const msg = messages[index];
      if (!msg) return;
      try {
        await navigator.clipboard.writeText(msg.text);
      } catch {
        /* ignore */
      }
    },
    [messages],
  );

  const rootClass = isFloat
    ? "cnexus-float-panel cnexus-float-chat relative h-full min-h-0 min-w-0 overflow-hidden"
    : `relative flex flex-col min-h-0 h-[420px] ${isCognitive ? "rounded-2xl" : "rounded-xl border shadow-sm"}`;

  const rootStyle: React.CSSProperties = isFloat
    ? { backgroundColor: t.chatBg, borderColor: t.border }
    : isCognitive
      ? { backgroundColor: t.chatBg }
      : {
          backgroundColor: t.surface,
          borderColor: t.border,
          borderTopWidth: 3,
          borderTopColor: t.blue,
        };

  const activeShare = shareIndex != null ? messages[shareIndex] : null;

  return (
    <div className={rootClass} style={rootStyle} data-cnexus-chat-panel>
      {!isCognitive && !isFloat && (
        <div
          className="px-4 py-2.5 border-b flex items-center justify-between gap-2 shrink-0"
          style={{ borderColor: t.border }}
        >
          <p className="text-sm font-semibold" style={{ color: t.blue }}>
            Chat 对话面板
          </p>
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-[10px]" style={{ color: isDemo ? t.orange : isLive ? t.green : t.red }}>
              {isDemo ? "Demo 离线" : isLive ? "Runtime 在线" : signals.health.connectionLabel}
            </span>
            <OllamaControlButton />
          </div>
        </div>
      )}

      <div
        className={`px-3 py-1.5 border-b shrink-0 truncate ${
          isFloat ? `${floatTy.caption} pr-3` : "px-4 py-2 flex flex-wrap gap-2 text-[10px]"
        }`}
        style={{
          borderColor: t.border,
          color: t.textMuted,
          backgroundColor: isFloat ? "rgba(0,0,0,0.12)" : isCognitive ? "transparent" : t.bg,
        }}
      >
        {isFloat ? (
          <span className="truncate block">
            目标: <b style={{ color: t.blue }}>{ctx.goal}</b>
            {" · "}
            信念: <b style={{ color: t.green }}>{ctx.belief}</b>
          </span>
        ) : (
          <>
            <span>
              目标: <b style={{ color: t.blue }}>{ctx.goal}</b>
            </span>
            <span>|</span>
            <span>
              信念: <b style={{ color: t.green }}>{ctx.belief}</b>
            </span>
            <span>|</span>
            <span>
              身份: <b style={{ color: t.text }}>{ctx.identity}</b>
            </span>
          </>
        )}
      </div>

      <div
        ref={messagesScrollRef}
        className={`min-h-0 overflow-y-auto overscroll-contain cnexus-float-scroll space-y-3 ${
          isFloat ? "px-3 py-3 mr-0.5" : "flex-1 min-h-0 p-4"
        }`}
        onContextMenu={(e) => e.preventDefault()}
      >
        {messages.length === 0 && (
          <p
            className={`text-center py-8 ${isFloat ? floatTy.body : "text-xs"}`}
            style={{ color: t.textMuted }}
          >
            {isFloat
              ? isDemo
                ? "演示模式对话 — 发送消息开始（示例上下文）"
                : "与 Runtime 上下文绑定的对话 — 发送消息开始"
              : isCognitive
                ? "流动对话层 — 与 canonical state 对话"
                : "与运行时上下文绑定的对话 — 发送消息开始"}
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "ml-auto max-w-[92%]" : "max-w-[92%]"}>
            <div
              className={`px-3 py-2 rounded-lg whitespace-pre-wrap break-words cursor-default select-text ${
                isFloat ? floatTy.body : "text-sm"
              }`}
              data-cnexus-chat-message
              style={
                m.role === "user"
                  ? { backgroundColor: t.blueSoft, color: t.text }
                  : {
                      backgroundColor: isCognitive ? t.surface : t.bg,
                      color: t.text,
                      border: `1px solid ${t.border}`,
                    }
              }
              onPointerDown={(e) => onMessagePointerDown(e, i)}
              onContextMenu={(e) => onMessageContextMenu(e, i)}
            >
              {m.text}
            </div>
            {m.meta && (
              <p
                className={`mt-1 px-1 ${isFloat ? floatTy.mono : "text-[10px]"}`}
                style={{ color: t.textLight, fontFamily: isFloat ? undefined : t.fontMono }}
              >
                {m.meta}
              </p>
            )}
          </div>
        ))}
      </div>

      <div
        className={`shrink-0 border-t ${isFloat ? "px-3 pt-2.5 pb-3" : "p-3"}`}
        style={{ borderColor: t.border, backgroundColor: isFloat ? t.surface : undefined }}
        data-no-drag
      >
        {!isDemo && runtimeGateHint && (
          <p
            className={`mb-2 px-3 py-2 rounded-lg border ${isFloat ? floatTy.caption : "text-xs"}`}
            style={{ borderColor: t.orange, color: t.orange, backgroundColor: t.orangeSoft }}
            role="status"
          >
            {runtimeGateHint}
          </p>
        )}
        {!isDemo && <ChatModelSelect compact={isFloat} className="mb-2" disabled={inputBlocked} />}
        <div className="flex gap-2 items-end min-w-0">
          <textarea
            ref={inputRef}
            rows={1}
            className={`flex-1 min-w-0 px-3 py-2 rounded-lg border outline-none box-border resize-none cnexus-float-scroll leading-relaxed ${
              isFloat ? floatTy.input : "text-sm"
            }`}
            style={{
              borderColor: t.border,
              color: t.text,
              backgroundColor: t.bg,
              maxHeight: isFloat ? 120 : 160,
              minHeight: 36,
            }}
            placeholder="输入你的问题或想法…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onInput={syncInputHeight}
            onKeyDown={(e) => {
              if (e.key !== "Enter") return;
              if (e.shiftKey) return;
              e.preventDefault();
              void send();
            }}
            disabled={inputBlocked}
          />
          <button
            type="button"
            className="w-9 h-9 rounded-lg flex items-center justify-center text-white shrink-0 disabled:opacity-50 box-border mb-0.5 transition-transform active:scale-95"
            style={{ backgroundColor: t.blue }}
            onClick={send}
            disabled={inputBlocked || !input.trim()}
            aria-label="发送"
            aria-busy={loading}
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </div>
        {!isCognitive && !isFloat && (
          <p className="text-[10px] mt-2" style={{ color: t.textLight }}>
            自动关联: 记忆检索 | 信念更新 | 目标进度 | 反思触发
          </p>
        )}
        {(isFloat || isCognitive) && (
          <p className={`mt-1.5 ${isFloat ? floatTy.caption : "text-[10px]"}`} style={{ color: t.textLight }}>
            Enter 发送 · Shift+Enter 换行
          </p>
        )}
      </div>

      {menu && (
        <ChatMessageMenu
          position={{ x: menu.x, y: menu.y }}
          onClose={() => setMenu(null)}
          onCopy={() => {
            void copyMessage(menu.index);
          }}
          onShare={() => {
            setShareIndex(menu.index);
            setMenu(null);
          }}
        />
      )}

      {activeShare && (
        <ChatShareDialog
          payload={buildChatSharePayload(activeShare.role, activeShare.text)}
          onClose={closeMenus}
        />
      )}

      {authPreview && (
        <ChatOutboundAuthorizationDialog
          preview={authPreview}
          loading={authLoading}
          onAuthorize={() => {
            const text = pendingUserTextRef.current;
            setInput("");
            requestAnimationFrame(() => {
              const el = inputRef.current;
              if (el) {
                el.style.height = "auto";
                el.style.overflowY = "hidden";
              }
            });
            void finalizeAuthorizedReply(
              authPreview.prepareId,
              text,
              pendingModelIdRef.current,
              "with_injection",
            );
          }}
          onSendUserOnly={() => {
            const text = pendingUserTextRef.current;
            setInput("");
            requestAnimationFrame(() => {
              const el = inputRef.current;
              if (el) {
                el.style.height = "auto";
                el.style.overflowY = "hidden";
              }
            });
            void finalizeAuthorizedReply(
              authPreview.prepareId,
              text,
              pendingModelIdRef.current,
              "user_only",
            );
          }}
          onCancel={() => void cancelAuthorization()}
        />
      )}
    </div>
  );
}
