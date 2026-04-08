"use client";

import { create } from "zustand";
import { immer } from "zustand/middleware/immer";

import type {
  A2UIPayload,
  ChatMessage,
  ConversationSummary,
  MessageContentBlock
} from "@/types/protocols";

interface ChatStore {
  messages: ChatMessage[];
  conversations: ConversationSummary[];
  isStreaming: boolean;
  currentStreamingId: string | null;
  conversationId: string | null;
  setConversationId: (id: string) => void;
  addUserMessage: (text: string) => void;
  startAssistantMessage: () => string;
  appendTextDelta: (id: string, delta: string) => void;
  appendA2UIBlock: (id: string, payload: A2UIPayload) => void;
  appendA2UISurface: (id: string, surfaceId: string) => void;
  setThinking: (id: string, thinking: boolean) => void;
  finalizeMessage: (id: string) => void;
  reset: () => void;
}

function createId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function findMessage(messages: ChatMessage[], id: string): ChatMessage | undefined {
  return messages.find((msg) => msg.id === id);
}

function removeThinking(content: MessageContentBlock[]): MessageContentBlock[] {
  return content.filter((block) => block.kind !== "thinking");
}

export const useChatStore = create<ChatStore>()(
  immer((set, get) => ({
    messages: [],
    conversations: [],
    isStreaming: false,
    currentStreamingId: null,
    conversationId: null,

    setConversationId: (id: string) =>
      set((state) => {
        state.conversationId = id;
      }),

    addUserMessage: (text: string) =>
      set((state) => {
        const now = Date.now();
        state.messages.push({
          id: createId("user"),
          role: "user",
          content: [{ kind: "text", text }],
          timestamp: now
        });

        if (!state.conversationId) {
          state.conversationId = createId("conv");
        }
        const existing = state.conversations.find((conv) => conv.id === state.conversationId);
        if (!existing) {
          state.conversations.unshift({
            id: state.conversationId,
            firstMessage: text.trim().slice(0, 80) || "New chat",
            createdAt: now
          });
        }
      }),

    startAssistantMessage: () => {
      const id = createId("assistant");
      set((state) => {
        state.isStreaming = true;
        state.currentStreamingId = id;
        state.messages.push({
          id,
          role: "assistant",
          content: [],
          timestamp: Date.now()
        });
      });
      return id;
    },

    appendTextDelta: (id: string, delta: string) =>
      set((state) => {
        const msg = findMessage(state.messages, id);
        if (!msg) {
          return;
        }
        msg.content = removeThinking(msg.content);
        const last = msg.content[msg.content.length - 1];
        if (last?.kind === "text") {
          last.text += delta;
        } else {
          msg.content.push({ kind: "text", text: delta });
        }
      }),

    appendA2UIBlock: (id: string, payload: A2UIPayload) =>
      set((state) => {
        const msg = findMessage(state.messages, id);
        if (!msg) {
          return;
        }
        msg.content = removeThinking(msg.content);
        msg.content.push({ kind: "a2ui", payload });
      }),

    appendA2UISurface: (id: string, surfaceId: string) =>
      set((state) => {
        const msg = findMessage(state.messages, id);
        if (!msg) {
          return;
        }
        msg.content = removeThinking(msg.content);
        const alreadyExists = msg.content.some(
          (block) => block.kind === "a2ui_surface" && block.surfaceId === surfaceId
        );
        if (!alreadyExists) {
          msg.content.push({ kind: "a2ui_surface", surfaceId });
        }
      }),

    setThinking: (id: string, thinking: boolean) =>
      set((state) => {
        const msg = findMessage(state.messages, id);
        if (!msg) {
          return;
        }
        const hasThinking = msg.content.some((block) => block.kind === "thinking");
        if (thinking && !hasThinking && msg.content.length === 0) {
          msg.content.push({ kind: "thinking" });
        }
        if (!thinking) {
          msg.content = removeThinking(msg.content);
        }
      }),

    finalizeMessage: (id: string) =>
      set((state) => {
        const msg = findMessage(state.messages, id);
        if (msg) {
          msg.content = removeThinking(msg.content);
        }
        if (state.currentStreamingId === id) {
          state.currentStreamingId = null;
          state.isStreaming = false;
        }
      }),

    reset: () => {
      const existingConversations = get().conversations;
      set((state) => {
        state.messages = [];
        state.isStreaming = false;
        state.currentStreamingId = null;
        state.conversationId = createId("conv");
        state.conversations = existingConversations;
      });
    }
  }))
);
