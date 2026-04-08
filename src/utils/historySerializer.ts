import type { ChatMessage } from "@/types/protocols";

export function serializeHistory(messages: ChatMessage[]): Array<Record<string, unknown>> {
  return messages.map((message) => {
    const content = message.content
      .map((block) => {
        if (block.kind === "text") {
          return block.text;
        }
        if (block.kind === "a2ui") {
          return `<a2ui>${JSON.stringify(block.payload)}</a2ui>`;
        }
        return "<thinking>Thinking...</thinking>";
      })
      .join("\n");

    return {
      role: message.role,
      content
    };
  });
}

