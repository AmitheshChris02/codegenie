"use client";

import ReactDiffViewer from "react-diff-viewer-continued";

type Props = {
  oldCode: string;
  newCode: string;
  language: string;
  filename?: string;
};

export default function DiffViewer({ oldCode, newCode, language, filename }: Props) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700">
      {filename && (
        <div className="border-b border-slate-200 px-4 py-2 text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400">
          {filename}
        </div>
      )}
      <ReactDiffViewer
        oldValue={oldCode}
        newValue={newCode}
        splitView={false}
        useDarkTheme
        hideLineNumbers={false}
      />
    </div>
  );
}
