"use client";

import { Star } from "lucide-react";

export function StarRatingInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <div>
      <span className="mb-1 block text-sm text-foreground">{label}</span>
      <div className="flex gap-1" role="radiogroup" aria-label={label}>
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            role="radio"
            aria-checked={value === n}
            aria-label={`${n} star${n === 1 ? "" : "s"}`}
            onClick={() => onChange(n)}
            className="rounded p-0.5 outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Star
              className={`size-5 ${n <= value ? "fill-signal-caution text-signal-caution" : "text-border"}`}
            />
          </button>
        ))}
      </div>
    </div>
  );
}
