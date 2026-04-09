"use client";

import type { A2UIAction, A2UIPayload } from "@/types/protocols";

import ActionCard from "../ui/ActionCard";
import CodeViewer from "../ui/CodeViewer";
import DiffViewer from "../ui/DiffViewer";
import MarkdownBlock from "../ui/MarkdownBlock";
import RechartGraph from "../ui/RechartGraph";

interface Props {
  payload: A2UIPayload;
  onAction?: (action: A2UIAction, payload: A2UIPayload) => Promise<void>;
}

function str(value: unknown, fallback = ""): string {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (value && typeof value === "object") {
    const o = value as Record<string, unknown>;
    if (typeof o.literalString === "string") return o.literalString;
  }
  return fallback;
}

export default function A2UIResolver({ payload, onAction }: Props) {
  const { componentName, componentData: d, aguiActions } = payload;

  switch (componentName) {
    case "MarkdownBlock": {
      const raw = d.markdown ?? d.text;
      return <MarkdownBlock markdown={str(raw)} />;
    }

    case "CodeViewer":
      return (
        <CodeViewer
          code={str(d.code)}
          language={str(d.language, "plaintext")}
          filename={d.filename ? str(d.filename) : undefined}
        />
      );

    case "DiffViewer":
      return (
        <DiffViewer
          oldCode={str(d.oldCode)}
          newCode={str(d.newCode)}
          language={str(d.language, "text")}
          filename={d.filename ? str(d.filename) : undefined}
        />
      );

    case "RechartGraph":
      return (
        <RechartGraph
          chartType={(str(d.chartType, "bar") as "bar" | "line" | "pie")}
          data={(d.data as Array<Record<string, unknown>>) ?? []}
          xKey={str(d.xKey, "name")}
          yKey={str(d.yKey, "value")}
          title={d.title ? str(d.title) : undefined}
        />
      );

    case "ActionCard":
      return (
        <ActionCard
          title={str(d.title, "Action")}
          description={str(d.description)}
          metadata={d.metadata as Record<string, unknown> | undefined}
          actions={aguiActions}
          onAction={async (action) => {
            if (!onAction) return;
            await onAction(action, payload);
          }}
        />
      );

    default:
      return null;
  }
}