"use client";

import ReactDiffViewer from "react-diff-viewer-continued";

type Props = {
  oldCode: string;
  newCode: string;
  language?: string;
  filename?: string;
};

export default function DiffViewer({ oldCode, newCode, language = "text", filename }: Props) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
      <div className="flex items-center justify-between border-b border-slate-200 px-3 py-2 text-xs dark:border-slate-700">
        <span className="font-medium text-slate-700 dark:text-slate-200">{filename ?? "Code Diff"}</span>
        <span className="rounded-full bg-slate-100 px-2 py-0.5 uppercase tracking-wide text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          {language}
        </span>
      </div>
      <div className="[&_.diff-code]:font-mono [&_.diff-code]:text-xs">
        <ReactDiffViewer oldValue={oldCode} newValue={newCode} splitView showDiffOnly={false} />
      </div>
    </div>
  );
}

