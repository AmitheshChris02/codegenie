"use client";

type Props = {
  text: string;
  isStreaming: boolean;
};

export default function StreamingText({ text, isStreaming }: Props) {
  return (
    <span className="whitespace-pre-wrap text-slate-800 dark:text-slate-100">
      {text}
      {isStreaming ? <span className="ml-0.5 animate-pulse text-brand-400">|</span> : null}
    </span>
  );
}

