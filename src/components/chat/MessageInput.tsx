"use client";

import { SendHorizonal } from "lucide-react";
import { FormEvent, KeyboardEvent, useState } from "react";

type Props = {
  disabled?: boolean;
  onSend: (text: string) => Promise<void>;
};

export default function MessageInput({ disabled = false, onSend }: Props) {
  const [text, setText] = useState("");

  async function submit() {
    const value = text.trim();
    if (!value || disabled) return;
    setText("");
    await onSend(value);
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await submit();
  }

  async function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      await submit();
    }
  }

  return (
    <form onSubmit={onSubmit} className="mx-auto w-full max-w-[920px] px-5 pb-5 pt-3">
      <div className="flex items-end gap-3 rounded-2xl border border-slate-300 bg-white p-3 shadow-soft dark:border-slate-700 dark:bg-slate-900">
        <textarea
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={onKeyDown}
          disabled={disabled}
          placeholder="Message CodeGenie"
          rows={1}
          className="max-h-48 min-h-11 flex-1 resize-y rounded-xl bg-transparent px-2 py-2 text-sm text-slate-900 outline-none placeholder:text-slate-500 disabled:opacity-60 dark:text-slate-100 dark:placeholder:text-slate-400"
        />
        <button
          type="submit"
          disabled={disabled || !text.trim()}
          className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600 text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-slate-400"
          aria-label="Send message"
        >
          <SendHorizonal size={18} />
        </button>
      </div>
    </form>
  );
}
