"use client";

import { useEffect, useState } from "react";

import type { TrustBand } from "@/lib/search/use-search";

const BAND_COLOR: Record<TrustBand, string> = {
  unrated: "var(--muted-foreground)",
  high_risk: "var(--signal-danger)",
  caution: "var(--signal-caution)",
  trusted: "var(--signal-verified)",
};

const SIZE = 140;
const STROKE = 12;
const RADIUS = (SIZE - STROKE) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export function TrustRing({ score, band }: { score: number | null; band: TrustBand }) {
  const [displayScore, setDisplayScore] = useState(0);
  const target = score ?? 0;

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) {
      setDisplayScore(target);
      return;
    }
    const durationMs = 600;
    const start = performance.now();
    let frame: number;

    const tick = (now: number) => {
      const progress = Math.min((now - start) / durationMs, 1);
      setDisplayScore(Math.round(progress * target));
      if (progress < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target]);

  const color = BAND_COLOR[band];
  const offset = score === null ? CIRCUMFERENCE : CIRCUMFERENCE * (1 - target / 100);

  return (
    <div
      className="relative inline-flex items-center justify-center"
      style={{ width: SIZE, height: SIZE }}
      role="img"
      aria-label={score === null ? "Unrated" : `Trust score ${score} out of 100`}
    >
      <svg width={SIZE} height={SIZE} className="-rotate-90">
        <circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={RADIUS}
          fill="none"
          stroke="var(--border)"
          strokeWidth={STROKE}
        />
        {score !== null ? (
          <circle
            cx={SIZE / 2}
            cy={SIZE / 2}
            r={RADIUS}
            fill="none"
            stroke={color}
            strokeWidth={STROKE}
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={offset}
            style={{ transition: "stroke-dashoffset 600ms ease-out" }}
          />
        ) : null}
      </svg>
      <div className="absolute flex flex-col items-center">
        <span
          className="font-heading text-3xl font-semibold"
          style={{ color: score === null ? "var(--muted-foreground)" : color }}
        >
          {score === null ? "—" : displayScore}
        </span>
        <span className="text-xs text-muted-foreground">
          {score === null ? "Unrated" : "/ 100"}
        </span>
      </div>
    </div>
  );
}
