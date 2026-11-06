"use client";

import { useEffect, useState } from "react";

import { BeliefNotes } from "@/components/sim/BeliefNotes";
import {
  ControlBar,
  type ReplaySpeed,
} from "@/components/sim/ControlBar";
import { RoundPanel } from "@/components/sim/RoundPanel";
import { RunChart } from "@/components/sim/RunChart";
import { SummaryStrip } from "@/components/sim/SummaryStrip";
import type { LedgerMode, Run } from "@/lib/types";

export interface SimulationViewProps {
  run: Run;
}

export function SimulationView({ run }: SimulationViewProps) {
  const total = run.rounds;

  const [cursor, setCursor] = useState(total);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<ReplaySpeed>(1);
  const [memoryView, setMemoryView] = useState<LedgerMode>("on");
  const [ruleRevealed, setRuleRevealed] = useState(false);

  const isPlaying = playing && cursor < total;

  useEffect(() => {
    if (!playing || cursor >= total) {
      return;
    }

    const timer = window.setTimeout(() => {
      setCursor((round) => Math.min(round + 1, total));
    }, 700 / speed);

    return () => window.clearTimeout(timer);
  }, [cursor, playing, speed, total]);

  function handleTogglePlay() {
    if (cursor >= total) {
      setCursor(0);
      setPlaying(true);
      setRuleRevealed(false);
      return;
    }

    setPlaying((value) => !value);
  }

  function handleRestart() {
    setCursor(0);
    setPlaying(true);
    setRuleRevealed(false);
  }

  return (
    <div className="space-y-8 sm:space-y-10">
      <header className="max-w-4xl">
        <p className="font-mono text-xs uppercase tracking-[0.35em] text-[#017587]">
          Simulation
        </p>
        <h1 className="mt-5 font-display text-4xl font-bold leading-[0.95] tracking-tight text-text-primary sm:text-6xl">
          Credit that learns from its own losses
        </h1>
        <p className="mt-5 max-w-3xl text-lg leading-8 text-text-secondary">
          Same 40 loan requests. Same agents. One underwriter remembers, the
          other does not.
        </p>
      </header>

      <ControlBar
        memoryView={memoryView}
        onMemoryViewChange={setMemoryView}
        isPlaying={isPlaying}
        onTogglePlay={handleTogglePlay}
        onRestart={handleRestart}
        speed={speed}
        onSpeedChange={setSpeed}
        cursor={cursor}
        total={total}
      />

      <SummaryStrip run={run} cursor={cursor} />

      <RunChart run={run} cursor={cursor} focus={memoryView} />

      <div className="grid gap-8 md:grid-cols-2 md:items-start">
        <RoundPanel run={run} cursor={cursor} />
        <BeliefNotes
          beliefs={run.beliefs}
          cursor={cursor}
          total={total}
          rule={run.ground_truth.rule}
          ruleRevealed={ruleRevealed}
          onRevealRule={() => setRuleRevealed(true)}
        />
      </div>

      <footer className="border-t-2 border-navy pt-4 font-mono text-xs tracking-wide text-text-secondary">
        Memory by Hindsight.
      </footer>
    </div>
  );
}
