"use client";

type Props = {
  componentName: string;
};

export default function ErrorFallback({ componentName }: Props) {
  return (
    <div className="rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
      Unsupported component received: <strong>{componentName}</strong>
    </div>
  );
}

