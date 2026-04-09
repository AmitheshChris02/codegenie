"use client";

import type { A2UIPayload } from "@/types/protocols";

import ActionCard from "../ui/ActionCard";
import CodeViewer from "../ui/CodeViewer";
import DiffViewer from "../ui/DiffViewer";
import ErrorFallback from "../ui/ErrorFallback";
import MarkdownBlock from "../ui/MarkdownBlock";
import RechartGraph from "../ui/RechartGraph";

interface Props {
  payload: A2UIPayload;
}

export default function A2UIResolver({ payload }: Props) {
  // Normalise built-in A2UI component names the model sometimes emits
  const name = (() => {
    switch (payload.componentName) {
      case "Text": return "MarkdownBlock";
      case "Card": return "ActionCard";
      default: return payload.componentName;
    }
  })();

  const data = payload.componentData;

  switch (name) {
    case "MarkdownBlock": {
      // Text component uses { text: { literalString: "..." } } or plain string
      const raw = data.markdown ?? data.text;
      const md = typeof raw === "object" && raw !== null
        ? String((raw as Record<string, unknown>).literalString ?? "")
        : String(raw ?? "");
      return <MarkdownBlock markdown={md} />;
    }

    case "CodeViewer":
      return (
        <CodeViewer
          code={String(data.code ?? "")}
          language={String(data.language ?? "plaintext")}
          filename={data.filename ? String(data.filename) : undefined}
        />
      );

    case "ActionCard":
      return (
        <ActionCard
          title={String(data.title ?? "Action Card")}
          description={String(data.description ?? "")}
          metadata={data.metadata as Record<string, unknown> | undefined}
          actions={payload.aguiActions}
          onAction={async () => undefined}
        />
      );

    case "RechartGraph":
      return (
        <RechartGraph
          chartType={(data.chartType as "bar" | "line" | "pie") ?? "bar"}
          data={(data.data as Array<Record<string, unknown>>) ?? []}
          xKey={data.xKey ? String(data.xKey) : "name"}
          yKey={data.yKey ? String(data.yKey) : "value"}
          title={data.title ? String(data.title) : undefined}
        />
      );

    case "DiffViewer":
      return (
        <DiffViewer
          oldCode={String(data.oldCode ?? "")}
          newCode={String(data.newCode ?? "")}
          language={data.language ? String(data.language) : "text"}
          filename={data.filename ? String(data.filename) : undefined}
        />
      );

    case "ThinkingBubble":
      return null;

    default:
      return <ErrorFallback componentName={payload.componentName} />;
  }
}
