"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";

export default function MarkdownBlock({ markdown }: { markdown: string }) {
  const [checkStates, setCheckStates] = useState<Record<number, boolean>>({});
  let checkIndex = 0;

  return (
    <div className="prose prose-slate max-w-none dark:prose-invert prose-pre:bg-slate-950 prose-pre:text-slate-100">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          input: ({ type, checked, ...props }) => {
            if (type === "checkbox") {
              const idx = checkIndex++;
              return (
                <input
                  type="checkbox"
                  checked={checkStates[idx] ?? checked ?? false}
                  onChange={(e) =>
                    setCheckStates((prev) => ({ ...prev, [idx]: e.target.checked }))
                  }
                  {...props}
                />
              );
            }
            return <input type={type} checked={checked} {...props} />;
          },
        }}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  );
}
