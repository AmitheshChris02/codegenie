"use client";

export default function ThinkingIndicator() {
  return (
    <div className="inline-flex items-center gap-1 rounded-full border border-slate-300 bg-white px-3 py-1 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
      <span className="h-1.5 w-1.5 animate-[pulse_1.2s_ease-in-out_infinite] rounded-full bg-brand-500" />
      <span className="h-1.5 w-1.5 animate-[pulse_1.2s_ease-in-out_0.2s_infinite] rounded-full bg-brand-500" />
      <span className="h-1.5 w-1.5 animate-[pulse_1.2s_ease-in-out_0.4s_infinite] rounded-full bg-brand-500" />
    </div>
  );
}
