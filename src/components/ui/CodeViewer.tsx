"use client";

import { Check, Copy } from "lucide-react";
import { useMemo, useState } from "react";
import hljs from "highlight.js";

type Props = {
  code: string;
  language?: string;
  filename?: string;
};

export default function CodeViewer({ code, language = "plaintext", filename }: Props) {
  const [copied, setCopied] = useState(false);

  const highlighted = useMemo(() => {
    try {
      if (hljs.getLanguage(language)) {
        return hljs.highlight(code, { language }).value;
      }
      return hljs.highlightAuto(code).value;
    } catch {
      return code;
    }
  }, [code, language]);

  async function onCopy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="relative overflow-hidden rounded-xl border border-slate-700 bg-slate-950 text-slate-100 shadow-soft">
      <div className="flex items-center justify-between border-b border-slate-800 px-3 py-2">
        <div className="flex items-center gap-2">
          {filename ? (
            <span className="rounded-full bg-slate-800 px-2 py-1 text-xs text-slate-300">{filename}</span>
          ) : null}
        </div>
        <button
          type="button"
          onClick={onCopy}
          className="rounded-md border border-slate-700 px-2 py-1 text-xs text-slate-200 transition hover:bg-slate-800"
        >
          <span className="inline-flex items-center gap-1">
            {copied ? <Check size={14} /> : <Copy size={14} />}
            {copied ? "Copied" : "Copy"}
          </span>
        </button>
      </div>

      <pre className="max-h-[420px] overflow-auto p-4 text-sm">
        <code dangerouslySetInnerHTML={{ __html: highlighted }} />
      </pre>

      <div className="absolute bottom-2 left-2 rounded-full bg-slate-800/85 px-2 py-1 text-[10px] uppercase tracking-wider text-slate-300">
        {language}
      </div>
    </div>
  );
}

