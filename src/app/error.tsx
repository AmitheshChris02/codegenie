"use client";

export default function GlobalError({
  error,
  reset
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html>
      <body className="min-h-screen bg-slate-100 p-6 dark:bg-slate-950">
        <div className="mx-auto max-w-xl rounded-xl border border-red-300 bg-white p-4 text-sm shadow dark:border-red-700 dark:bg-slate-900">
          <h2 className="text-base font-semibold text-red-700 dark:text-red-300">Application Error</h2>
          <p className="mt-2 text-slate-700 dark:text-slate-300">{error.message}</p>
          <button
            type="button"
            onClick={() => reset()}
            className="mt-4 rounded-lg bg-red-600 px-3 py-1.5 text-white"
          >
            Try Again
          </button>
        </div>
      </body>
    </html>
  );
}

