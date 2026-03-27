"use client";

import { PROVIDERS } from "@/lib/providers/metadata";

interface Props {
  selected: string[];
  onChange: (ids: string[]) => void;
  disabled?: boolean;
}

export default function ModelCheckboxGroup({ selected, onChange, disabled }: Props) {
  const toggle = (id: string) => {
    if (selected.includes(id)) {
      // Never allow deselecting the last one
      if (selected.length <= 1) return;
      onChange(selected.filter((s) => s !== id));
    } else {
      // Max 2 selected
      if (selected.length >= 2) return;
      onChange([...selected, id]);
    }
  };

  const atMax = selected.length >= 2;

  return (
    <div className="flex gap-2 flex-wrap">
      {PROVIDERS.map((p) => {
        const isSelected = selected.includes(p.id);
        const isDisabled = disabled || (!isSelected && atMax);
        return (
          <button
            key={p.id}
            type="button"
            onClick={() => !isDisabled && toggle(p.id)}
            disabled={isDisabled}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
              isSelected
                ? "bg-indigo-600/20 border-indigo-500/50 text-indigo-300"
                : "bg-zinc-800 border-zinc-700 text-zinc-400 hover:border-zinc-500 hover:text-zinc-200"
            } disabled:opacity-40 disabled:cursor-not-allowed`}
          >
            <span className="flex items-center gap-1.5">
              <span
                className={`w-3.5 h-3.5 rounded border flex items-center justify-center shrink-0 ${
                  isSelected
                    ? "bg-indigo-500 border-indigo-400"
                    : "border-zinc-600"
                }`}
              >
                {isSelected && (
                  <svg
                    className="w-2.5 h-2.5 text-white"
                    viewBox="0 0 10 10"
                    fill="none"
                  >
                    <path
                      d="M2 5l2.5 2.5L8 3"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                )}
              </span>
              {p.label}
            </span>
          </button>
        );
      })}
      {atMax && !disabled && (
        <span className="self-center text-xs text-zinc-600 ml-1">max. 2</span>
      )}
    </div>
  );
}
