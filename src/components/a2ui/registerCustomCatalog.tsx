"use client";

import {
  ComponentRegistry,
  initializeDefaultCatalog,
  type A2UIComponentProps,
  useA2UIComponent,
} from "@a2ui/react";
import type { Types } from "@a2ui/react";
import { injectStyles } from "@a2ui/react/styles";

import ActionCard from "@/components/ui/ActionCard";
import CodeViewer from "@/components/ui/CodeViewer";
import DiffViewer from "@/components/ui/DiffViewer";
import MarkdownBlock from "@/components/ui/MarkdownBlock";
import RechartGraph from "@/components/ui/RechartGraph";

type AGUIAction = {
  label: string;
  intent?: string;
  name?: string;
  parameters?: Record<string, unknown>;
  style?: "primary" | "danger" | "default";
};

function getProperties(node: A2UIComponentProps["node"]): Record<string, unknown> {
  const raw = (node as { properties?: unknown }).properties;
  return typeof raw === "object" && raw !== null ? (raw as Record<string, unknown>) : {};
}

function unwrapValue(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => unwrapValue(item));
  }

  if (!value || typeof value !== "object") {
    return value;
  }

  const obj = value as Record<string, unknown>;

  if (typeof obj.literalString === "string") return obj.literalString;
  if (typeof obj.literalNumber === "number") return obj.literalNumber;
  if (typeof obj.literalBoolean === "boolean") return obj.literalBoolean;

  if (Array.isArray(obj.explicitList)) {
    return obj.explicitList.map((item) => unwrapValue(item));
  }

  const result: Record<string, unknown> = {};
  for (const [key, nested] of Object.entries(obj)) {
    result[key] = unwrapValue(nested);
  }
  return result;
}

function toPlainString(value: unknown, fallback = ""): string {
  const unwrapped = unwrapValue(value);
  if (typeof unwrapped === "string") return unwrapped;
  if (typeof unwrapped === "number" || typeof unwrapped === "boolean") return String(unwrapped);
  return fallback;
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

  return {
    name: String(action.intent ?? action.name ?? "ACTION"),
    context: contextEntries,
  };
}

function normalizeChartType(value: unknown): "bar" | "line" | "pie" {
  const normalized = toPlainString(value, "bar").trim().toLowerCase();
  if (normalized.includes("line")) return "line";
  if (normalized.includes("pie") || normalized.includes("donut") || normalized.includes("doughnut")) return "pie";
  return "bar";
}

function parseData(raw: unknown): Array<Record<string, unknown>> {
  const unwrapped = unwrapValue(raw);

  if (Array.isArray(unwrapped)) {
    return unwrapped.filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null);
  }

  if (typeof unwrapped === "string") {
    try {
      const parsed = JSON.parse(unwrapped);
      if (Array.isArray(parsed)) {
        return parsed.filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null);
      }
      if (parsed && typeof parsed === "object") {
        return Object.entries(parsed as Record<string, unknown>).map(([name, value]) => ({ name, value }));
      }
    } catch {
      return [];
    }
  }

  if (unwrapped && typeof unwrapped === "object") {
    return Object.entries(unwrapped as Record<string, unknown>).map(([name, value]) => ({ name, value }));
  }

  return [];
}

function extractMarkdownLinks(text: string): Array<{ label: string; url: string }> {
  const matches = Array.from(text.matchAll(/\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g));
  return matches.map((match) => ({ label: match[1].trim(), url: match[2].trim() }));
}

function normalizeActionsFromProps(props: Record<string, unknown>): AGUIAction[] {
  const primary = Array.isArray(props.aguiActions) ? (props.aguiActions as AGUIAction[]) : [];
  if (primary.length > 0) return primary;

  if (Array.isArray(props.actions)) {
    const actions = (props.actions as Array<Record<string, unknown>>)
      .map((action) => {
        const label = String(action.label ?? action.title ?? action.text ?? "").trim();
        const intent = String(action.intent ?? action.name ?? "").trim();
        const url = String(action.url ?? action.href ?? "").trim();
        if (!label && !intent && !url) return null;

        return {
          label: label || "Action",
          intent: intent || (url ? "OPEN_LINK" : "ACTION"),
          parameters: {
            ...(typeof action.parameters === "object" && action.parameters !== null
              ? (action.parameters as Record<string, unknown>)
              : {}),
            ...(url ? { url } : {}),
          },
          style: (action.style as "primary" | "danger" | "default" | undefined) ?? "default",
        } satisfies AGUIAction;
      })
      .filter((item) => item !== null) as AGUIAction[];

    if (actions.length > 0) return actions;
  }

  const directUrl = String(props.url ?? props.href ?? "").trim();
  if (directUrl) {
    return [
      {
        label: "Open Link",
        intent: "OPEN_LINK",
        parameters: { url: directUrl },
        style: "primary",
      },
    ];
  }

  const description = String(props.description ?? "");
  const links = extractMarkdownLinks(description);
  if (links.length > 0) {
    return links.slice(0, 4).map((link) => ({
      label: link.label || "Open Link",
      intent: "OPEN_LINK",
      parameters: { url: link.url },
      style: "default",
    }));
  }

  return [];
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

  return (
    <RechartGraph
      chartType={normalizeChartType(props.chartType)}
      data={parseData(props.data)}
      xKey={toPlainString(props.xKey ?? props.x ?? props.categoryKey ?? props.labelKey, "name")}
      yKey={toPlainString(props.yKey ?? props.y ?? props.valueKey ?? props.metricKey, "value")}
      title={props.title ? toPlainString(props.title) : undefined}
    />
  );
}

function ActionCardA2UI({ node, surfaceId }: A2UIComponentProps) {
  const props = getProperties(node);
  const { sendAction } = useA2UIComponent(node, surfaceId);
  const actions = normalizeActionsFromProps(props);
  const source = (props.metadata as Record<string, unknown> | undefined) ?? props;

  return (
    <ActionCard
      title={String(props.title ?? "Action")}
      description={String(props.description ?? "")}
      metadata={props.metadata as Record<string, unknown> | undefined}
      actions={actions.map((action) => ({
        label: String(action.label ?? "Action"),
        intent: String(action.intent ?? action.name ?? "ACTION"),
        parameters: (action.parameters as Record<string, unknown>) ?? {},
        style: action.style ?? "default",
      }))}
      onAction={async (action) => {
        sendAction(
          toA2UIAction(
            {
              label: action.label,
              intent: action.intent,
              parameters: action.parameters,
              style: action.style,
            },
            source
          )
        );
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

  injectStyles();
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