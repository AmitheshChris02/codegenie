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
      {isStreaming ? (
        <span className="ml-1 inline-block h-5 w-0.5 animate-pulse bg-brand-600 align-middle dark:bg-brand-300" />
      ) : null}
    </div>
  );
}
