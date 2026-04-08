"use client";

import "highlight.js/styles/github-dark.css";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";

type Props = {
  markdown: string;
};

type TaskCheckboxProps = {
  checked?: boolean | null;
};

function TaskCheckbox({ checked }: TaskCheckboxProps) {
  const [isChecked, setIsChecked] = useState(Boolean(checked));
  return (
    <input
      type="checkbox"
      checked={isChecked}
      onChange={(event) => setIsChecked(event.target.checked)}
      className="mr-2 h-4 w-4 cursor-pointer align-middle"
    />
  );
}

export default function MarkdownBlock({ markdown }: Props) {
  return (
    <div className="prose prose-slate max-w-none dark:prose-invert prose-pre:rounded-xl prose-pre:bg-slate-900 prose-code:before:content-[''] prose-code:after:content-['']">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          input: ({ type, checked }) => {
            if (type === "checkbox") {
              return <TaskCheckbox checked={checked} />;
            }
            return <input type={type} />;
          }
        }}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  );
}
