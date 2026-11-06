"use client";

import { clsx } from "clsx";
import { Pause, Play, RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/Button";
import type { LedgerMode } from "@/lib/types";

export type ReplaySpeed = 1 | 2 | 4;

const focusRing =
  "focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-accent";

const views: Array<{ mode: LedgerMode; label: string }> = [
  { mode: "on", label: "Memory on" },
  { mode: "off", label: "Memory off" },
];

const speeds: ReplaySpeed[] = [1, 2, 4];

export interface ControlBarProps {
  memoryView: LedgerMode;
  onMemoryViewChange: (mode: LedgerMode) => void;
  isPlaying: boolean;
  onTogglePlay: () => void;
  onRestart: () => void;
  speed: ReplaySpeed;
  onSpeedChange: (speed: ReplaySpeed) => void;
  cursor: number;
  total: number;
}

export function ControlBar({
  memoryView,
  onMemoryViewChange,
  isPlaying,
  onTogglePlay,
  onRestart,
  speed,
  onSpeedChange,
  cursor,
  total,
}: ControlBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div
        role="tablist"
        aria-label="Memory view"
        className="inline-flex border-2 border-navy"
      >
        {views.map((view) => {
          const selected = memoryView === view.mode;

          return (
            <button
              key={view.mode}
              type="button"
              role="tab"
              aria-selected={selected}
              tabIndex={selected ? 0 : -1}
              onClick={() => onMemoryViewChange(view.mode)}
              onKeyDown={(event) => {
                if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
                  event.preventDefault();
                  onMemoryViewChange(view.mode === "on" ? "off" : "on");
                }
              }}
              className={clsx(
                "px-4 py-2 font-mono text-xs uppercase tracking-widest transition-colors",
                focusRing,
                selected
                  ? "bg-navy text-cream"
                  : "bg-transparent text-navy hover:bg-surface",
              )}
            >
              {view.label}
            </button>
          );
        })}
      </div>

      <Button
        variant="primary"
        icon={
          isPlaying ? (
            <Pause className="h-4 w-4" aria-hidden="true" />
          ) : (
            <Play className="h-4 w-4" aria-hidden="true" />
          )
        }
        onClick={onTogglePlay}
        className={focusRing}
      >
        {isPlaying ? "Pause" : "Play"}
      </Button>

      <Button
        variant="secondary"
        icon={<RotateCcw className="h-4 w-4" aria-hidden="true" />}
        onClick={onRestart}
        className={focusRing}
      >
        Restart
      </Button>

      <div className="inline-flex items-center">
        <span className="mr-2 font-mono text-[10px] uppercase tracking-widest text-text-secondary">
          Speed
        </span>
        <div
          role="group"
          aria-label="Replay speed"
          className="inline-flex border-2 border-navy"
        >
          {speeds.map((option) => (
            <button
              key={option}
              type="button"
              aria-pressed={speed === option}
              onClick={() => onSpeedChange(option)}
              className={clsx(
                "px-3 py-2 font-mono text-xs uppercase tracking-widest transition-colors",
                focusRing,
                speed === option
                  ? "bg-navy text-cream"
                  : "bg-transparent text-navy hover:bg-surface",
              )}
            >
              {option}x
            </button>
          ))}
        </div>
      </div>

      <div className="ml-auto font-mono text-xs uppercase tracking-widest text-text-primary">
        Round {cursor} / {total}
      </div>
    </div>
  );
}
