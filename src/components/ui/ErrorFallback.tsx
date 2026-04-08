"use client";

export default function ErrorFallback({ componentName }: { componentName: string }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-600 dark:border-red-800 dark:bg-red-950/30 dark:text-red-400">
      Unknown component: <code>{componentName}</code>
    </div>
  );
}
