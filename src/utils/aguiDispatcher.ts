import { useChatStore } from "@/store/chatStore";
import type { AGUIPayload, InteractionType } from "@/types/protocols";

import { serializeHistory } from "./historySerializer";
import { streamChat } from "./sseClient";

export async function dispatchAGUI(
  intent: string,
  context: Record<string, unknown>,
  interactionType: InteractionType = "BUTTON_CLICK"
): Promise<void> {
  const store = useChatStore.getState();
  const aguiPayload: AGUIPayload = {
    protocol: "AGUI",
    interaction_type: interactionType,
    intent,
    context
  };

  const streamingId = store.startAssistantMessage();
  const history = serializeHistory(store.messages);

  await streamChat(
    {
      message: aguiPayload,
      history,
      conversation_id: store.conversationId
    },
    {
      onTextDelta: (delta) => useChatStore.getState().appendTextDelta(streamingId, delta),
      onA2UI: (payload) => useChatStore.getState().appendA2UIBlock(streamingId, payload),
      onThinking: () => useChatStore.getState().setThinking(streamingId, true),
      onDone: () => useChatStore.getState().finalizeMessage(streamingId),
      onError: (error) => {
        useChatStore.getState().appendTextDelta(streamingId, `\n\nError: ${error}`);
      }
    }
  );
}

