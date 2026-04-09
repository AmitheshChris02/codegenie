"use client";

import { A2UIRenderer } from "@a2ui/react";
import type { ChatMessage } from "@/types/protocols";

import A2UIResolver from "./A2UIResolver";
import ThinkingIndicator from "./ThinkingIndicator";
import MarkdownBlock from "../ui/MarkdownBlock";
import StreamingText from "../ui/StreamingText";

type Props = {
  messages: ChatMessage[];
  currentStreamingId: string | null;
  showSkeleton: boolean;
};

function Skeleton() {
  return (
    <div className="space-y-4">
      <div className="h-6 w-1/2 animate-pulse rounded bg-slate-200 dark:bg-slate-800" />
      <div className="h-32 w-full animate-pulse rounded-xl bg-slate-200 dark:bg-slate-800" />
      <div className="ml-auto h-10 w-2/3 animate-pulse rounded-2xl bg-slate-200 dark:bg-slate-800" />
    </div>
  );
}

export default function MessageList({ messages, currentStreamingId, showSkeleton }: Props) {
  if (showSkeleton) return <Skeleton />;

  if (messages.length === 0) {
    return (
      <div className="mt-24 text-center text-sm text-slate-600 dark:text-slate-300">
        Start with a prompt like: <span className="font-medium">&quot;Compare REST vs GraphQL&quot;</span>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {messages.map((message) => {
        const isUser = message.role === "user";
        const isStreaming = currentStreamingId === message.id;
        return (
          <div key={message.id} className={isUser ? "flex justify-end" : "flex justify-start"} data-role={message.role}>
            {isUser ? (
              <div className="max-w-[86%] whitespace-pre-wrap rounded-2xl bg-slate-900 px-4 py-2.5 text-sm leading-6 text-white dark:bg-brand-700">
                {message.content.map((block, index) =>
                  block.kind === "text" ? <span key={`${message.id}-${index}`}>{block.text}</span> : null
                )}
              </div>
            ) : (
              <div className="w-full space-y-4">
                {message.content.length === 0 && isStreaming ? <ThinkingIndicator /> : null}
                {message.content.map((block, index) => {
                  if (block.kind === "thinking") {
                    return <ThinkingIndicator key={`${message.id}-${index}`} />;
                  }

                  if (block.kind === "text") {
                    return (
                      <div key={`${message.id}-${index}`} className="w-full rounded-xl bg-white/80 px-4 py-3 shadow-sm dark:bg-slate-900/65">
                        {isStreaming ? (
                          <StreamingText text={block.text} isStreaming={isStreaming} />
                        ) : (
                          <MarkdownBlock markdown={block.text} />
                        )}
                      </div>
                    );
                  }

                  if (block.kind === "a2ui_surface") {
                    return (
                      <div key={`${message.id}-${index}`} className="w-full overflow-visible rounded-xl border border-slate-200 bg-white p-3 shadow-sm dark:border-slate-800 dark:bg-slate-900">
                        <A2UIRenderer surfaceId={block.surfaceId} />
                      </div>
                    );
                  }

                  if (block.kind === "a2ui") {
                    return <A2UIResolver key={`${message.id}-${index}`} payload={block.payload} />;
                  }

                  return null;
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

