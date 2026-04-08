import type { AGUIPayload, A2UIPayload, SSEEvent } from "@/types/protocols";

type StreamRequest = {
  message: string | AGUIPayload;
  history: Array<Record<string, unknown>>;
  conversation_id: string | null;
};

type StreamCallbacks = {
  onTextDelta: (delta: string) => void;
  onA2UI: (payload: A2UIPayload) => void;
  onThinking: () => void;
  onDone: () => void;
  onError: (error: string) => void;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function handleEvent(raw: string, callbacks: StreamCallbacks): boolean {
  if (!raw.trim()) {
    return false;
  }

  try {
    const parsed = JSON.parse(raw) as SSEEvent;
    switch (parsed.event) {
      case "text_delta":
        callbacks.onTextDelta(String(parsed.data ?? ""));
        return false;
      case "a2ui":
        callbacks.onA2UI(parsed.data as A2UIPayload);
        return false;
      case "thinking":
        callbacks.onThinking();
        return false;
      case "error":
        callbacks.onError(String(parsed.data ?? "Unknown streaming error"));
        return false;
      case "done":
        callbacks.onDone();
        return true;
      default:
        return false;
    }
  } catch (error) {
    callbacks.onError(`Failed to parse SSE event: ${String(error)}`);
    return false;
  }
}

function extractEvents(buffer: string): { rest: string; events: string[] } {
  const events: string[] = [];
  // SSE commonly uses CRLF line endings; normalize so delimiter parsing is stable.
  const normalized = buffer.replace(/\r/g, "");
  const chunks = normalized.split("\n\n");
  const rest = chunks.pop() ?? "";

  for (const chunk of chunks) {
    const lines = chunk.split("\n");
    const dataLines = lines
      .map((line) => line.trim())
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trim());
    if (dataLines.length > 0) {
      events.push(dataLines.join("\n"));
    }
  }

  return { rest, events };
}

export async function streamChat(request: StreamRequest, callbacks: StreamCallbacks): Promise<void> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream"
    },
    body: JSON.stringify(request)
  });

  if (!response.ok) {
    callbacks.onError(`Request failed with status ${response.status}`);
    callbacks.onDone();
    return;
  }

  if (!response.body) {
    callbacks.onError("No stream body returned by server");
    callbacks.onDone();
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const parsed = extractEvents(buffer);
    buffer = parsed.rest;

    for (const eventRaw of parsed.events) {
      const shouldStop = handleEvent(eventRaw, callbacks);
      if (shouldStop) {
        return;
      }
    }
  }

  if (buffer.trim()) {
    const parsed = extractEvents(`${buffer}\n\n`);
    for (const eventRaw of parsed.events) {
      const shouldStop = handleEvent(eventRaw, callbacks);
      if (shouldStop) {
        return;
      }
    }
  }

  callbacks.onDone();
}
