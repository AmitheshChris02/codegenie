export type A2UIAction = {
  label: string;
  intent: string;
  parameters?: Record<string, unknown>;
  style?: "primary" | "danger" | "default";
};

export type A2UIPayload = {
  componentName: string;
  componentData: Record<string, unknown>;
  aguiActions: A2UIAction[];
};

export type ContentBlock =
  | { kind: "text"; text: string }
  | { kind: "thinking" }
  | { kind: "a2ui_surface"; surfaceId: string }
  | { kind: "a2ui"; payload: A2UIPayload };

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: ContentBlock[];
};
