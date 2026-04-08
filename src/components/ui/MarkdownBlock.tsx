"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";

function checkboxKeyFromNode(node: unknown): string {
  const maybeNode = node as { position?: { start?: { line?: number; column?: number } } } | undefined;
  const line = maybeNode?.position?.start?.line;
  const column = maybeNode?.position?.start?.column;
  if (typeof line === "number" && typeof column === "number") {
    return `${line}:${column}`;
  }
  return "fallback";
}

export default function MarkdownBlock({ markdown }: { markdown: string }) {
  const [checkStates, setCheckStates] = useState<Record<string, boolean>>({});

  return (
    <div className="w-full text-[15px] leading-7 text-slate-800 dark:text-slate-100">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          h1: ({ children }) => <h1 className="mb-4 mt-6 text-3xl font-semibold tracking-tight first:mt-0">{children}</h1>,
          h2: ({ children }) => <h2 className="mb-3 mt-6 text-2xl font-semibold tracking-tight first:mt-0">{children}</h2>,
          h3: ({ children }) => <h3 className="mb-2 mt-5 text-xl font-semibold tracking-tight first:mt-0">{children}</h3>,
          h4: ({ children }) => <h4 className="mb-2 mt-4 text-lg font-semibold tracking-tight first:mt-0">{children}</h4>,
          p: ({ children }) => <p className="mb-4 last:mb-0">{children}</p>,
          ul: ({ children }) => <ul className="mb-4 list-disc space-y-1 pl-6">{children}</ul>,
          ol: ({ children }) => <ol className="mb-4 list-decimal space-y-1 pl-6">{children}</ol>,
          li: ({ children }) => <li className="pl-1">{children}</li>,
          blockquote: ({ children }) => (
            <blockquote className="mb-4 rounded-r-lg border-l-4 border-brand-500 bg-brand-50/50 px-4 py-2 text-slate-700 dark:bg-brand-900/20 dark:text-slate-200">
              {children}
            </blockquote>
          ),
          hr: () => <hr className="my-5 border-slate-300 dark:border-slate-700" />,
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noreferrer"
              className="font-medium text-brand-700 underline decoration-brand-400 underline-offset-4 hover:text-brand-600 dark:text-brand-300"
            >
              {children}
            </a>
          ),
          table: ({ children }) => (
            <div className="mb-4 overflow-x-auto rounded-xl border border-slate-300 dark:border-slate-700">
              <table className="min-w-full border-collapse text-sm">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="bg-slate-100 dark:bg-slate-800">{children}</thead>,
          tbody: ({ children }) => <tbody className="bg-white dark:bg-slate-900">{children}</tbody>,
          th: ({ children }) => (
            <th className="border-b border-slate-300 px-3 py-2 text-left font-semibold text-slate-800 dark:border-slate-700 dark:text-slate-100">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border-b border-slate-200 px-3 py-2 align-top text-slate-700 dark:border-slate-800 dark:text-slate-200">
              {children}
            </td>
          ),
          pre: ({ children }) => (
            <pre className="mb-4 overflow-x-auto rounded-xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-100">
              {children}
            </pre>
          ),
          code: (props) => {
            const { inline, className, children, ...codeProps } = props as {
              inline?: boolean;
              className?: string;
              children?: unknown;
            } & Record<string, unknown>;

            if (inline) {
              return (
                <code
                  className="rounded-md bg-slate-200 px-1.5 py-0.5 text-[13px] text-slate-900 dark:bg-slate-800 dark:text-slate-100"
                  {...(codeProps as any)}
                >
                  {children}
                </code>
              );
            }

            return (
              <code className={className} {...(codeProps as any)}>
                {children}
              </code>
            );
          },
          input: (props) => {
            const { type, checked, node, ...inputProps } = props as {
              type?: string;
              checked?: boolean;
              node?: unknown;
            } & Record<string, unknown>;

            if (type === "checkbox") {
              const key = checkboxKeyFromNode(node);
              const value = checkStates[key] ?? Boolean(checked);
              return (
                <input
                  type="checkbox"
                  className="mr-2 h-4 w-4 accent-brand-600"
                  checked={value}
                  onChange={(event) => {
                    const nextValue = event.target.checked;
                    setCheckStates((prev) => ({ ...prev, [key]: nextValue }));
                  }}
                  {...(inputProps as any)}
                />
              );
            }

            return <input type={type} checked={checked} {...(inputProps as any)} />;
          },
        }}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  );
}


