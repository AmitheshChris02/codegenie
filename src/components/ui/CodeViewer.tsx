"use client";

import { useEffect, useRef, useState } from "react";
import hljs from "highlight.js";

type Props = {
  code: string;
  language: string;
  filename?: string;
};

export default function CodeViewer({ code, language, filename }: Props) {
  const ref = useRef<HTMLElement>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (ref.current) {
      hljs.highlightElement(ref.current);
    }
  }, [code, language]);

  async function copy() {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-slate-950 dark:border-slate-700">
      {filename && (
        <div className="flex items-center justify-between border-b border-slate-700 px-4 py-2">
          <span className="text-xs text-slate-400">{filename}</span>
          <button
            type="button"
            onClick={copy}
            className="text-xs text-slate-400 hover:text-slate-200"
          >
            {copied ? "Copied!" : "Copy"}
          </button>
        </div>
      )}
      <pre className="overflow-x-auto p-4 text-sm">
        <code ref={ref} className={`language-${language}`}>
          {code}
        </code>
      </pre>
    </div>
  );
}
