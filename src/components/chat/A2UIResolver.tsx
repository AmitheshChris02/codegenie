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
  switch (payload.componentName) {
    case "MarkdownBlock":
      return <MarkdownBlock markdown={String(payload.componentData.markdown ?? "")} />;

    case "CodeViewer":
      return (
        <CodeViewer
          code={String(payload.componentData.code ?? "")}
          language={String(payload.componentData.language ?? "plaintext")}
          filename={payload.componentData.filename ? String(payload.componentData.filename) : undefined}
        />
      );

    case "ActionCard":
      return (
        <ActionCard
          title={String(payload.componentData.title ?? "Action Card")}
          description={String(payload.componentData.description ?? "")}
          metadata={payload.componentData.metadata as Record<string, unknown> | undefined}
          actions={payload.aguiActions}
          onAction={async () => undefined}
        />
      );

    case "RechartGraph":
      return (
        <RechartGraph
          chartType={(payload.componentData.chartType as "bar" | "line" | "pie") ?? "bar"}
          data={(payload.componentData.data as Array<Record<string, unknown>>) ?? []}
          xKey={payload.componentData.xKey ? String(payload.componentData.xKey) : "name"}
          yKey={payload.componentData.yKey ? String(payload.componentData.yKey) : "value"}
          title={payload.componentData.title ? String(payload.componentData.title) : undefined}
        />
      );

    case "DiffViewer":
      return (
        <DiffViewer
          oldCode={String(payload.componentData.oldCode ?? "")}
          newCode={String(payload.componentData.newCode ?? "")}
          language={payload.componentData.language ? String(payload.componentData.language) : "text"}
          filename={payload.componentData.filename ? String(payload.componentData.filename) : undefined}
        />
      );

    default:
      return <ErrorFallback componentName={payload.componentName} />;
  }
}
