"use client";

import MarkdownBlock from "./MarkdownBlock";

export default function StreamingText({
  text,
  isStreaming,
}: {
  text: string;
  isStreaming: boolean;
}) {
  return (
    <div className="relative">
      <MarkdownBlock markdown={text} />
      {isStreaming && (
        <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-slate-600 dark:bg-slate-300" />
      )}
    </div>
  );
}
