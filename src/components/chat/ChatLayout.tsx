"use client";

import { HttpAgent, type AgentSubscriber } from "@ag-ui/client";
import type { AssistantMessage, UserMessage } from "@ag-ui/core";
import { A2UIProvider, useA2UIActions } from "@a2ui/react";
import type { Types as A2UITypes } from "@a2ui/react";
import { Menu, MessageSquarePlus, MoonStar, PanelLeftClose, PanelLeftOpen, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { v4 as uuidv4 } from "uuid";

import { registerCustomA2UIComponents } from "@/components/a2ui/registerCustomCatalog";
import { useChatStore } from "@/store/chatStore";

import MessageInput from "./MessageInput";
import MessageList from "./MessageList";

const MODEL_BADGE = process.env.NEXT_PUBLIC_MODEL_NAME ?? "anthropic.claude-3-5-sonnet-20241022-v2:0";
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8009";
const A2UI_CUSTOM_EVENT_NAME = "A2UI_MESSAGES";

registerCustomA2UIComponents();

type A2UIActionHandler = (message: A2UITypes.A2UIClientEventMessage) => Promise<void>;

function createUserMessage(content: string): UserMessage {
  return {
    id: `user-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    role: "user",
    content,
  };
}

function createAssistantMemoryMessage(content: string): AssistantMessage {
  return {
    id: `assistant-mem-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    role: "assistant",
    content,
  };
}

function isA2UIMessage(value: unknown): value is A2UITypes.ServerToClientMessage {
  if (!value || typeof value !== "object") return false;
  const message = value as Record<string, unknown>;
  return (
    "beginRendering" in message ||
    "surfaceUpdate" in message ||
    "dataModelUpdate" in message ||
    "deleteSurface" in message
  );
}

function tryParseJson(value: unknown): unknown {
  if (typeof value !== "string") return value;
  const trimmed = value.trim();
  if (!trimmed) return value;
  if (!(trimmed.startsWith("{") && trimmed.endsWith("}")) && !(trimmed.startsWith("[") && trimmed.endsWith("]"))) return value;
  try {
    return JSON.parse(trimmed);
  } catch {
    return value;
  }
}

function normalizeA2UIMessages(value: unknown): A2UITypes.ServerToClientMessage[] {
  const parsed = tryParseJson(value);
  if (Array.isArray(parsed)) return parsed.filter(isA2UIMessage);
  if (!parsed || typeof parsed !== "object") return [];
  if (isA2UIMessage(parsed)) return [parsed];
  const envelope = parsed as Record<string, unknown>;
  if (Array.isArray(envelope.messages)) return envelope.messages.filter(isA2UIMessage);
  if (Array.isArray(envelope.value)) return envelope.value.filter(isA2UIMessage);
  if (envelope.value) return normalizeA2UIMessages(envelope.value);
  return [];
}

function extractSurfaceIds(messages: A2UITypes.ServerToClientMessage[]): string[] {
  const ids = new Set<string>();
  for (const message of messages) {
    if (message.beginRendering?.surfaceId) ids.add(String(message.beginRendering.surfaceId));
    if (message.surfaceUpdate?.surfaceId) ids.add(String(message.surfaceUpdate.surfaceId));
    if (message.dataModelUpdate?.surfaceId) ids.add(String(message.dataModelUpdate.surfaceId));
  }
  return Array.from(ids);
}

function getLiteralString(value: unknown): string {
  if (typeof value === "string") return value;
  if (!value || typeof value !== "object") return "";
  const asRecord = value as Record<string, unknown>;
  if (typeof asRecord.literalString === "string") return asRecord.literalString;
  return "";
}

function summarizeComponent(componentName: string, rawProps: unknown): string | null {
  const props = typeof rawProps === "object" && rawProps !== null ? (rawProps as Record<string, unknown>) : {};

  if (componentName === "Text") {
    const text = getLiteralString(props.text).trim();
    return text || null;
  }

  if (componentName === "MarkdownBlock") {
    const text = String(props.markdown ?? "").trim();
    if (!text) return null;
    return text.slice(0, 1200);
  }

  if (componentName === "CodeViewer") {
    const filename = props.filename ? ` (${String(props.filename)})` : "";
    const language = props.language ? ` [${String(props.language)}]` : "";
    return `Code snippet${filename}${language}`;
  }

  if (componentName === "DiffViewer") {
    const filename = props.filename ? ` (${String(props.filename)})` : "";
    const language = props.language ? ` [${String(props.language)}]` : "";
    return `Code diff${filename}${language}`;
  }

  if (componentName === "RechartGraph") {
    const title = props.title ? `: ${String(props.title)}` : "";
    const chartType = props.chartType ? ` (${String(props.chartType)})` : "";
    return `Chart${chartType}${title}`;
  }

  if (componentName === "ActionCard") {
    const title = String(props.title ?? "Action").trim();
    const description = String(props.description ?? "").trim();
    const actions = Array.isArray(props.aguiActions)
      ? (props.aguiActions as Array<Record<string, unknown>>)
          .map((item) => String(item.label ?? item.intent ?? ""))
          .filter((v) => v.trim().length > 0)
      : [];

    const actionsPart = actions.length > 0 ? ` | Actions: ${actions.join(", ")}` : "";
    return `${title}${description ? ` - ${description}` : ""}${actionsPart}`.trim();
  }

  if (componentName === "Button") {
    const action = props.action as Record<string, unknown> | undefined;
    if (action && typeof action.name === "string" && action.name.trim()) {
      return `Button action: ${action.name}`;
    }
    return "Button action";
  }

  return null;
}

function extractA2UIContextSnippets(messages: A2UITypes.ServerToClientMessage[]): string[] {
  const snippets: string[] = [];

  for (const message of messages) {
    const components = message.surfaceUpdate?.components;
    if (!Array.isArray(components)) continue;

    for (const componentInstance of components) {
      const instance = componentInstance as { id?: unknown; component?: unknown };
      if (instance.id === "root") continue;
      if (!instance.component || typeof instance.component !== "object") continue;

      const entries = Object.entries(instance.component as Record<string, unknown>);
      if (entries.length === 0) continue;

      const [componentName, componentProps] = entries[0];
      const summary = summarizeComponent(componentName, componentProps);
      if (summary && summary.trim()) snippets.push(summary.trim());
    }
  }

  return Array.from(new Set(snippets));
}

function actionToPrompt(actionMessage: A2UITypes.A2UIClientEventMessage): string {
  const action = actionMessage.userAction;
  if (!action) return "User triggered a UI action.";
  return [
    `UI Action: ${action.name}`,
    `Source: ${action.sourceComponentId}`,
    `Surface: ${action.surfaceId}`,
    `Context: ${JSON.stringify(action.context ?? {})}`,
  ].join("\n");
}

function ChatLayoutShell({ actionHandlerRef }: { actionHandlerRef: React.MutableRefObject<A2UIActionHandler | null> }) {
  const { resolvedTheme, setTheme } = useTheme();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showSkeleton, setShowSkeleton] = useState(true);
  const [autoScroll, setAutoScroll] = useState(true);
  const [mounted, setMounted] = useState(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const agentRef = useRef<HttpAgent | null>(null);
  const activeThreadRef = useRef<string | null>(null);

  const { processMessages, clearSurfaces } = useA2UIActions();

  const messages = useChatStore((state) => state.messages);
  const conversations = useChatStore((state) => state.conversations);
  const isStreaming = useChatStore((state) => state.isStreaming);
  const currentStreamingId = useChatStore((state) => state.currentStreamingId);
  const conversationId = useChatStore((state) => state.conversationId);
  const setConversationId = useChatStore((state) => state.setConversationId);
  const addUserMessage = useChatStore((state) => state.addUserMessage);
  const startAssistantMessage = useChatStore((state) => state.startAssistantMessage);
  const appendTextDelta = useChatStore((state) => state.appendTextDelta);
  const appendA2UISurface = useChatStore((state) => state.appendA2UISurface);
  const setThinking = useChatStore((state) => state.setThinking);
  const finalizeMessage = useChatStore((state) => state.finalizeMessage);
  const reset = useChatStore((state) => state.reset);

  useEffect(() => {
    if (!conversationId) setConversationId(uuidv4());
  }, [conversationId, setConversationId]);

  useEffect(() => {
    const timer = setTimeout(() => setShowSkeleton(false), 450);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    const node = bottomRef.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (entry) setAutoScroll(entry.isIntersecting);
      },
      { threshold: 0.7 }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (autoScroll) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [messages, currentStreamingId, autoScroll]);

  const activeConversationLabel = useMemo(() => {
    if (!conversationId) return "No conversation";
    return conversationId.slice(0, 8);
  }, [conversationId]);

  const ensureAgent = useCallback((threadId: string): HttpAgent => {
    if (!agentRef.current || activeThreadRef.current !== threadId) {
      agentRef.current = new HttpAgent({ url: `${API_BASE}/chat`, threadId });
      activeThreadRef.current = threadId;
    }
    return agentRef.current;
  }, []);

  const runAssistantTurn = useCallback(
    async (params: { userText?: string; actionMessage?: A2UITypes.A2UIClientEventMessage }) => {
      const currentConversationId = useChatStore.getState().conversationId ?? uuidv4();
      if (!conversationId) setConversationId(currentConversationId);

      const agent = ensureAgent(currentConversationId);

      if (params.userText) {
        addUserMessage(params.userText);
        agent.addMessage(createUserMessage(params.userText));
      }
      if (params.actionMessage?.userAction) {
        agent.addMessage(createUserMessage(actionToPrompt(params.actionMessage)));
      }

      const runId = uuidv4();
      const streamingId = startAssistantMessage();
      const renderedSurfaces = new Set<string>();
      const a2uiSnippetsForMemory: string[] = [];
      let assistantTextBuffer = "";
      let finalized = false;

      const persistAssistantMemory = () => {
        if (assistantTextBuffer.trim().length > 0) return;
        if (a2uiSnippetsForMemory.length === 0) return;
        const summary = Array.from(new Set(a2uiSnippetsForMemory)).join("\n\n").trim();
        if (!summary) return;
        agent.addMessage(createAssistantMemoryMessage(summary));
      };

      const finish = () => {
        if (!finalized) {
          finalizeMessage(streamingId);
          finalized = true;
        }
      };

      const subscriber: AgentSubscriber = {
        onReasoningStartEvent: () => {
          setThinking(streamingId, true);
        },
        onReasoningMessageContentEvent: () => {
          setThinking(streamingId, true);
        },
        onReasoningEndEvent: () => {
          setThinking(streamingId, false);
        },
        onTextMessageContentEvent: ({ event }) => {
          const delta = String(event.delta ?? "");
          assistantTextBuffer += delta;
          appendTextDelta(streamingId, delta);
        },
        onCustomEvent: ({ event }) => {
          if (event.name !== A2UI_CUSTOM_EVENT_NAME) return;
          const rawPayload = event.value ?? (event as { data?: unknown }).data ?? (event as { rawEvent?: unknown }).rawEvent;
          const a2uiMessages = normalizeA2UIMessages(rawPayload);
          if (a2uiMessages.length === 0) return;

          const snippets = extractA2UIContextSnippets(a2uiMessages);
          if (snippets.length > 0) a2uiSnippetsForMemory.push(...snippets);

          processMessages(a2uiMessages);
          for (const surfaceId of extractSurfaceIds(a2uiMessages)) {
            if (!renderedSurfaces.has(surfaceId)) {
              appendA2UISurface(streamingId, surfaceId);
              renderedSurfaces.add(surfaceId);
            }
          }
        },
        onRunErrorEvent: ({ event }) => {
          appendTextDelta(streamingId, `\n\nError: ${event.message}`);
          finish();
        },
        onRunFinishedEvent: () => {
          persistAssistantMemory();
          finish();
        },
      };

      try {
        await agent.runAgent(
          { runId, forwardedProps: params.actionMessage ? { a2uiAction: params.actionMessage } : {} },
          subscriber
        );
        finish();
      } catch (error) {
        appendTextDelta(streamingId, `\n\nError: ${String(error)}`);
        finish();
      }
    },
    [
      addUserMessage,
      appendA2UISurface,
      appendTextDelta,
      conversationId,
      ensureAgent,
      finalizeMessage,
      processMessages,
      setConversationId,
      setThinking,
      startAssistantMessage,
    ]
  );

  const handleSend = useCallback(async (text: string) => {
    await runAssistantTurn({ userText: text });
  }, [runAssistantTurn]);

  const handleAction = useCallback<A2UIActionHandler>(async (actionMessage) => {
    await runAssistantTurn({ actionMessage });
  }, [runAssistantTurn]);

  useEffect(() => {
    actionHandlerRef.current = handleAction;
    return () => {
      if (actionHandlerRef.current === handleAction) actionHandlerRef.current = null;
    };
  }, [actionHandlerRef, handleAction]);

  const handleNewChat = useCallback(() => {
    clearSurfaces();
    agentRef.current = null;
    activeThreadRef.current = null;
    reset();
  }, [clearSurfaces, reset]);

  return (
    <div className="relative min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_top,_rgba(76,176,176,0.16),_transparent_44%),radial-gradient(circle_at_bottom_right,_rgba(34,98,101,0.12),_transparent_40%)]" />

      <div className="mx-auto flex min-h-screen w-full max-w-[1400px]">
        <aside
          className={`border-r border-slate-200 bg-white/80 backdrop-blur dark:border-slate-800 dark:bg-slate-950/70 ${
            sidebarOpen ? "w-72" : "w-16"
          } transition-all duration-300`}
        >
          <div className="flex items-center justify-between px-3 py-3">
            <button
              type="button"
              onClick={() => setSidebarOpen((v) => !v)}
              className="rounded-lg border border-slate-300 p-2 text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
              aria-label="Toggle sidebar"
            >
              {sidebarOpen ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
            </button>
            {sidebarOpen ? <span className="text-xs text-slate-500 dark:text-slate-300">Conversations</span> : null}
          </div>

          {sidebarOpen ? (
            <div className="space-y-2 px-3 pb-4">
              {conversations.length === 0 ? (
                <div className="rounded-lg border border-dashed border-slate-300 p-3 text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400">
                  Conversations will appear here.
                </div>
              ) : (
                conversations.map((conv) => (
                  <div
                    key={conv.id}
                    className="rounded-lg border border-slate-200 bg-white p-2 text-xs shadow-sm dark:border-slate-700 dark:bg-slate-900"
                  >
                    <p className="font-medium text-slate-700 dark:text-slate-100">{conv.id.slice(0, 8)}</p>
                    <p className="mt-1 truncate text-slate-500 dark:text-slate-300">{conv.firstMessage}</p>
                  </div>
                ))
              )}
            </div>
          ) : (
            <div className="px-3 pt-2">
              <Menu className="text-slate-400" size={16} />
            </div>
          )}
        </aside>

        <section className="relative flex min-h-screen min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/85 px-5 py-3 backdrop-blur dark:border-slate-800 dark:bg-slate-950/80">
            <div className="mx-auto flex w-full max-w-[920px] items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-3">
                <h1 className="truncate text-lg font-semibold tracking-tight">CodeGenie</h1>
                <span className="hidden rounded-full border border-slate-300 px-2 py-1 text-[10px] uppercase tracking-wider text-slate-600 dark:border-slate-700 dark:text-slate-300 md:inline-flex">
                  {MODEL_BADGE}
                </span>
                <span className="rounded-full bg-brand-50 px-2 py-1 text-[10px] font-semibold text-brand-700 dark:bg-brand-900/40 dark:text-brand-200">
                  {activeConversationLabel}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleNewChat}
                  disabled={isStreaming}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-3 py-1.5 text-xs text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                >
                  <MessageSquarePlus size={14} />
                  New Chat
                </button>
                <button
                  type="button"
                  onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
                  className="rounded-lg border border-slate-300 p-2 text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                  aria-label="Toggle dark mode"
                >
                  {mounted ? (
                    resolvedTheme === "dark" ? <Sun size={16} /> : <MoonStar size={16} />
                  ) : (
                    <MoonStar size={16} />
                  )}
                </button>
              </div>
            </div>
          </header>

          <main className="flex-1 overflow-y-auto px-5 pb-40 pt-6">
            <div className="mx-auto w-full max-w-[920px]">
              <MessageList messages={messages} currentStreamingId={currentStreamingId} showSkeleton={showSkeleton} />
              <div ref={bottomRef} className="h-1 w-full" />
            </div>
          </main>

          <div className="sticky bottom-0 z-20 border-t border-slate-200 bg-white/88 backdrop-blur dark:border-slate-800 dark:bg-slate-950/88">
            <MessageInput disabled={isStreaming} onSend={handleSend} />
          </div>
        </section>
      </div>
    </div>
  );
}

export default function ChatLayout() {
  const actionHandlerRef = useRef<A2UIActionHandler | null>(null);

  const handleA2UIAction = useCallback((message: A2UITypes.A2UIClientEventMessage) => {
    if (!actionHandlerRef.current) return;
    void actionHandlerRef.current(message);
  }, []);

  return (
    <A2UIProvider onAction={handleA2UIAction}>
      <ChatLayoutShell actionHandlerRef={actionHandlerRef} />
    </A2UIProvider>
  );
}
