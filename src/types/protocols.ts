export type InteractionType = "BUTTON_CLICK" | "NODE_SELECT" | "FORM_SUBMIT";

export interface AGUIPayload {
  protocol: "AGUI";
  interaction_type: InteractionType;
  intent: string;
  context: Record<string, unknown>;
}

export interface A2UIAction {
  label: string;
  intent: string;
  parameters: Record<string, unknown>;
  style?: "primary" | "danger" | "default";
}

export type ComponentName =
  | "MarkdownBlock"
  | "CodeViewer"
  | "ActionCard"
  | "RechartGraph"
  | "DiffViewer"
  | "ThinkingBubble";

export interface A2UIPayload {
  type: "A2UI";
  componentName: ComponentName;
  componentData: Record<string, unknown>;
  aguiActions: A2UIAction[];
}

export type MessageRole = "user" | "assistant";

export type MessageContentBlock =
  | { kind: "text"; text: string }
  | { kind: "a2ui"; payload: A2UIPayload }
  | { kind: "a2ui_surface"; surfaceId: string }
  | { kind: "thinking" };

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: MessageContentBlock[];
  timestamp: number;
}

export interface ConversationSummary {
  id: string;
  firstMessage: string;
  createdAt: number;
}

export interface SSEEvent {
  event: "text_delta" | "a2ui" | "done" | "error" | "thinking";
  data: unknown;
}
