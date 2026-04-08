"use client";

import {
  ComponentRegistry,
  initializeDefaultCatalog,
  type A2UIComponentProps,
  useA2UIComponent,
} from "@a2ui/react";
import type { Types } from "@a2ui/react";

import ActionCard from "@/components/ui/ActionCard";
import CodeViewer from "@/components/ui/CodeViewer";
import DiffViewer from "@/components/ui/DiffViewer";
import MarkdownBlock from "@/components/ui/MarkdownBlock";
import RechartGraph from "@/components/ui/RechartGraph";

type AGUIAction = {
  label: string;
  intent: string;
  parameters?: Record<string, unknown>;
  style?: "primary" | "danger" | "default";
};

function getProperties(node: A2UIComponentProps["node"]): Record<string, unknown> {
  const raw = (node as { properties?: unknown }).properties;
  return typeof raw === "object" && raw !== null ? (raw as Record<string, unknown>) : {};
}

function toActionValue(value: unknown): { literalString?: string; literalNumber?: number; literalBoolean?: boolean } {
  if (typeof value === "boolean") return { literalBoolean: value };
  if (typeof value === "number") return { literalNumber: value };
  if (typeof value === "string") return { literalString: value };
  return { literalString: JSON.stringify(value) };
}

function toA2UIAction(action: AGUIAction, source?: Record<string, unknown>): Types.Action {
  const contextEntries = Object.entries(action.parameters ?? {}).map(([key, value]) => ({
    key,
    value: toActionValue(value),
  }));
  if (source && Object.keys(source).length > 0) {
    contextEntries.push({ key: "_source", value: { literalString: JSON.stringify(source) } });
  }
  return { name: action.intent, context: contextEntries };
}

function MarkdownBlockA2UI({ node }: A2UIComponentProps) {
  const props = getProperties(node);
  return <MarkdownBlock markdown={String(props.markdown ?? "")} />;
}

function CodeViewerA2UI({ node }: A2UIComponentProps) {
  const props = getProperties(node);
  return (
    <CodeViewer
      code={String(props.code ?? "")}
      language={String(props.language ?? "plaintext")}
      filename={props.filename ? String(props.filename) : undefined}
    />
  );
}

function DiffViewerA2UI({ node }: A2UIComponentProps) {
  const props = getProperties(node);
  return (
    <DiffViewer
      oldCode={String(props.oldCode ?? "")}
      newCode={String(props.newCode ?? "")}
      language={String(props.language ?? "text")}
      filename={props.filename ? String(props.filename) : undefined}
    />
  );
}

function RechartGraphA2UI({ node }: A2UIComponentProps) {
  const props = getProperties(node);
  let data = (props.data as Array<Record<string, unknown>>) ?? [];
  // Model sometimes sends data as a JSON string — parse it
  if (typeof data === "string") {
    try { data = JSON.parse(data as unknown as string); } catch { data = []; }
  }
  return (
    <RechartGraph
      chartType={(props.chartType as "bar" | "line" | "pie") ?? "bar"}
      data={Array.isArray(data) ? data : []}
      xKey={props.xKey ? String(props.xKey) : "name"}
      yKey={props.yKey ? String(props.yKey) : "value"}
      title={props.title ? String(props.title) : undefined}
    />
  );
}

function ActionCardA2UI({ node, surfaceId }: A2UIComponentProps) {
  const props = getProperties(node);
  const { sendAction } = useA2UIComponent(node, surfaceId);
  const actions = Array.isArray(props.aguiActions) ? (props.aguiActions as AGUIAction[]) : [];
  const source = (props.metadata as Record<string, unknown> | undefined) ?? props;

  return (
    <ActionCard
      title={String(props.title ?? "Action")}
      description={String(props.description ?? "")}
      metadata={props.metadata as Record<string, unknown> | undefined}
      actions={actions.map((action) => ({
        label: String(action.label ?? "Action"),
        intent: String(action.intent ?? "ACTION"),
        parameters: (action.parameters as Record<string, unknown>) ?? {},
        style: action.style ?? "default",
      }))}
      onAction={async (action) => {
        sendAction(toA2UIAction({ label: action.label, intent: action.intent, parameters: action.parameters, style: action.style }, source));
      }}
    />
  );
}

function ThinkingBubbleA2UI({ node }: A2UIComponentProps) {
  const props = getProperties(node);
  return (
    <div className="rounded-lg border border-dashed border-slate-300 px-3 py-2 text-xs text-slate-500 dark:border-slate-700 dark:text-slate-300">
      {String(props.text ?? "Thinking...")}
    </div>
  );
}

let registered = false;

export function registerCustomA2UIComponents(): void {
  if (registered) return;
  initializeDefaultCatalog();
  const registry = ComponentRegistry.getInstance();
  registry.register("MarkdownBlock", { component: MarkdownBlockA2UI });
  registry.register("CodeViewer", { component: CodeViewerA2UI });
  registry.register("DiffViewer", { component: DiffViewerA2UI });
  registry.register("RechartGraph", { component: RechartGraphA2UI });
  registry.register("ActionCard", { component: ActionCardA2UI });
  registry.register("ThinkingBubble", { component: ThinkingBubbleA2UI });
  registered = true;
}
