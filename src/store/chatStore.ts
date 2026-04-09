import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import { v4 as uuidv4 } from "uuid";
import type { ChatMessage, ContentBlock } from "@/types/protocols";

type Conversation = {
  id: string;
  firstMessage: string;
};

type ChatState = {
  messages: ChatMessage[];
  conversations: Conversation[];
  conversationId: string | null;
  isStreaming: boolean;
  currentStreamingId: string | null;

  setConversationId: (id: string) => void;
  addUserMessage: (text: string) => void;
  startAssistantMessage: () => string;
  appendTextDelta: (id: string, delta: string) => void;
  appendA2UISurface: (id: string, surfaceId: string) => void;
  appendA2UIComponent: (id: string, payload: import("@/types/protocols").A2UIPayload) => void;
  setThinking: (id: string, thinking: boolean) => void;
  finalizeMessage: (id: string) => void;
  reset: () => void;
};

export const useChatStore = create<ChatState>()(
  immer((set) => ({
    messages: [],
    conversations: [],
    conversationId: null,
    isStreaming: false,
    currentStreamingId: null,

    setConversationId: (id) =>
      set((state) => {
        state.conversationId = id;
      }),

    addUserMessage: (text) =>
      set((state) => {
        const msg: ChatMessage = {
          id: `user-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          role: "user",
          content: [{ kind: "text", text }],
        };
        state.messages.push(msg);
        if (state.conversationId && state.conversations.length === 0) {
          state.conversations.push({
            id: state.conversationId,
            firstMessage: text.slice(0, 60),
          });
        }
      }),

    startAssistantMessage: () => {
      const id = uuidv4();
      set((state) => {
        state.messages.push({ id, role: "assistant", content: [] });
        state.isStreaming = true;
        state.currentStreamingId = id;
      });
      return id;
    },

    appendTextDelta: (id, delta) =>
      set((state) => {
        const msg = state.messages.find((m) => m.id === id);
        if (!msg) return;
        const last = msg.content[msg.content.length - 1];
        if (last && last.kind === "text") {
          last.text += delta;
        } else {
          msg.content.push({ kind: "text", text: delta });
        }
      }),

    appendA2UISurface: (id, surfaceId) =>
      set((state) => {
        const msg = state.messages.find((m) => m.id === id);
        if (!msg) return;
        msg.content.push({ kind: "a2ui_surface", surfaceId });
      }),

    appendA2UIComponent: (id, payload) =>
      set((state) => {
        const msg = state.messages.find((m) => m.id === id);
        if (!msg) return;
        msg.content.push({ kind: "a2ui", payload });
      }),

    setThinking: (id, thinking) =>
      set((state) => {
        const msg = state.messages.find((m) => m.id === id);
        if (!msg) return;
        const hasThinking = msg.content.some((b) => b.kind === "thinking");
        if (thinking && !hasThinking) {
          msg.content.push({ kind: "thinking" });
        } else if (!thinking) {
          msg.content = msg.content.filter((b) => b.kind !== "thinking");
        }
      }),

    finalizeMessage: (id) =>
      set((state) => {
        if (state.currentStreamingId === id) {
          state.isStreaming = false;
          state.currentStreamingId = null;
        }
      }),

    reset: () =>
      set((state) => {
        const prevId = state.conversationId;
        state.messages = [];
        state.isStreaming = false;
        state.currentStreamingId = null;
        state.conversationId = uuidv4();
        if (prevId) {
          state.conversations = state.conversations.filter((c) => c.id !== prevId);
        }
      }),
  }))
);
