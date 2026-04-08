"use client";

import { LoaderCircle } from "lucide-react";
import { useState } from "react";

import type { A2UIAction } from "@/types/protocols";

type Props = {
  title: string;
  description: string;
  metadata?: Record<string, unknown>;
  actions: A2UIAction[];
  onAction: (action: A2UIAction) => Promise<void> | void;
};

function buttonClass(style?: A2UIAction["style"]): string {
  if (style === "primary") {
    return "bg-brand-600 text-white border-brand-600 hover:bg-brand-700";
  }
  if (style === "danger") {
    return "border-red-400 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20";
  }
  return "border-slate-300 text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800";
}

export default function ActionCard({ title, description, metadata, actions, onAction }: Props) {
  const [activeAction, setActiveAction] = useState<string | null>(null);

  async function handleAction(action: A2UIAction) {
    setActiveAction(action.label);
    try {
      await onAction(action);
    } finally {
      setActiveAction(null);
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <h3 className="text-[15px] font-semibold text-slate-900 dark:text-slate-100">{title}</h3>
      <p className="mt-1 text-[13px] text-slate-600 dark:text-slate-300">{description}</p>

      {metadata && Object.keys(metadata).length > 0 ? (
        <div className="mt-3 space-y-1 rounded-lg bg-slate-50 p-2 text-xs dark:bg-slate-800/50">
          {Object.entries(metadata).map(([key, value]) => (
            <div key={key} className="grid grid-cols-[100px_1fr] gap-2">
              <span className="font-medium text-slate-500 dark:text-slate-400">{key}</span>
              <span className="text-slate-700 dark:text-slate-200">{String(value)}</span>
            </div>
          ))}
        </div>
      ) : null}

      <div className="mt-4 flex flex-wrap gap-2">
        {actions.map((action) => {
          const isLoading = activeAction === action.label;
          return (
            <button
              key={`${action.intent}-${action.label}`}
              type="button"
              disabled={isLoading}
              onClick={() => handleAction(action)}
              className={`inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm transition disabled:opacity-70 ${buttonClass(
                action.style
              )}`}
            >
              {isLoading ? <LoaderCircle className="animate-spin" size={14} /> : null}
              {action.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

