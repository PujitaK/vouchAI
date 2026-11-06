"use client";

import { clsx } from "clsx";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { StickyNote } from "@/components/ui/StickyNote";
import { ClampedMiniMarkdown } from "@/lib/miniMarkdown";
import type { Belief } from "@/lib/types";

const focusRing =
  "focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-accent";

const rotations = [-2, 1.5, -1];

export interface BeliefNotesProps {
  beliefs: Belief[];
  cursor: number;
  total: number;
  rule: string;
  ruleRevealed: boolean;
  onRevealRule: () => void;
}

export function BeliefNotes({
  beliefs,
  cursor,
  total,
  rule,
  ruleRevealed,
  onRevealRule,
}: BeliefNotesProps) {
  const visibleBeliefs = beliefs.filter(
    (belief) => belief.after_round <= cursor,
  );

  return (
    <section className="min-w-0">
      <h2 className="mb-3 font-display text-xl font-bold tracking-tight text-text-primary">
        What memory learned
      </h2>

      {visibleBeliefs.length > 0 ? (
        <div className="space-y-4">
          {visibleBeliefs.map((belief, index) => (
            <StickyNote
              key={`${belief.after_round}-${index}`}
              rotationDeg={rotations[index % rotations.length]}
              className="text-sm leading-6 text-text-primary"
            >
              <p className="font-mono text-[10px] uppercase tracking-widest text-text-secondary">
                After round {belief.after_round}
              </p>
              <ClampedMiniMarkdown
                text={belief.text}
                className="mt-2 text-sm leading-6 text-text-primary"
              />
            </StickyNote>
          ))}
        </div>
      ) : (
        <div className="border-2 border-navy bg-cream p-4">
          <p className="font-mono text-xs uppercase tracking-widest text-text-secondary">
            No beliefs revealed yet.
          </p>
        </div>
      )}

      <Button
        variant="secondary"
        onClick={onRevealRule}
        disabled={cursor < total || ruleRevealed}
        className={clsx("mt-6", focusRing)}
      >
        Reveal hidden rule
      </Button>

      {ruleRevealed ? (
        <Card tilt="left" className="mt-6">
          <p className="font-mono text-[10px] uppercase tracking-widest text-text-secondary">
            Hidden rule
          </p>
          <p className="mt-3 text-sm leading-6 text-text-primary">{rule}</p>
        </Card>
      ) : null}
    </section>
  );
}
