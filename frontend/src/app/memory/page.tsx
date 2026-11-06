"use client";

import { clsx } from "clsx";
import { useState } from "react";

import { formatMoney, formatMultiplier } from "@/components/sim/format";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { StatusDot } from "@/components/ui/StatusDot";
import { getOnRows, getRetainedOnRows } from "@/lib/aggregate";
import { ClampedMiniMarkdown } from "@/lib/miniMarkdown";
import { useRun } from "@/lib/useRun";

const focusRing =
  "focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-accent";

const headCell =
  "border-b-2 border-navy bg-surface px-3 py-3 font-mono text-[10px] uppercase tracking-[0.18em] text-text-secondary";

const bodyCell = "border-b border-navy/20 px-3 py-3";

export default function MemoryPage() {
  const { run, loading, error } = useRun();
  const [showAllEvents, setShowAllEvents] = useState(false);
  const [ruleRevealed, setRuleRevealed] = useState(false);

  if (loading) {
    return (
      <div className="py-16 font-mono text-xs uppercase tracking-[0.2em] text-text-secondary">
        Loading memory inspector...
      </div>
    );
  }

  if (!run) {
    return (
      <Card tilt="left" className="max-w-xl">
        <p className="font-mono text-xs uppercase tracking-widest text-text-secondary">
          Memory inspector unavailable
        </p>
        <p className="mt-3 text-sm leading-6 text-text-primary">
          The cached run at{" "}
          <span className="font-mono">/cached_run.json</span> could not be
          loaded. Add the completed run to{" "}
          <span className="font-mono">frontend/public/</span> and refresh.
        </p>
        {error ? (
          <p className="mt-3 font-mono text-xs text-maroon">{error}</p>
        ) : null}
      </Card>
    );
  }

  const retainedEvents = getRetainedOnRows(run);
  const visibleEvents = showAllEvents
    ? retainedEvents
    : retainedEvents.slice(0, 20);
  const onRows = getOnRows(run);

  return (
    <section className="py-8">
      <header className="mb-12 max-w-3xl">
        <p className="font-mono text-xs uppercase tracking-[0.35em] text-[#017587]">
          Memory inspector
        </p>
        <h1 className="mt-4 font-display text-4xl font-bold tracking-tight text-text-primary sm:text-5xl">
          What the underwriter believes
        </h1>
        <p className="mt-5 text-lg leading-8 text-text-secondary">
          Beliefs, events, and the rule that was never written down.
        </p>
      </header>

      <div className="space-y-14">
        <section aria-labelledby="beliefs-heading">
          <h2
            id="beliefs-heading"
            className="font-display text-2xl font-bold uppercase tracking-[0.12em] text-text-primary"
          >
            Beliefs
          </h2>

          {run.beliefs.length > 0 ? (
            <div className="mt-6">
              {run.beliefs.map((belief, index) => (
                <div
                  key={`${belief.after_round}-${index}`}
                  className="relative border-l-2 border-navy pb-8 pl-6 last:pb-0"
                >
                  <span
                    className="absolute -left-[9px] top-0 h-4 w-4 border-2 border-navy bg-accent"
                    aria-hidden="true"
                  />
                  <p className="font-mono text-xs uppercase tracking-[0.2em] text-text-secondary">
                    Round {belief.after_round}
                  </p>
                  <Card
                    tilt={index % 2 === 0 ? "left" : "right"}
                    className="mt-3"
                  >
                    <ClampedMiniMarkdown
                      text={belief.text}
                      className="text-sm leading-6 text-text-primary"
                    />
                  </Card>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-6 font-mono text-xs uppercase tracking-widest text-text-secondary">
              No beliefs recorded.
            </p>
          )}
        </section>

        <section aria-labelledby="retained-events-heading">
          <h2
            id="retained-events-heading"
            className="font-display text-2xl font-bold uppercase tracking-[0.12em] text-text-primary"
          >
            Retained events
          </h2>

          <ul className="mt-6 border-t-2 border-navy">
            {visibleEvents.map((row) => (
              <li
                key={row.round}
                className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-navy/20 py-3"
              >
                <StatusDot status={row.outcome} label={row.outcome} />
                <p className="font-mono text-xs leading-6 text-text-primary">
                  Round {row.round}: {row.agent} ({row.principal},{" "}
                  {row.category}) lent {formatMoney(row.amount)}.
                </p>
              </li>
            ))}
          </ul>

          {retainedEvents.length > 20 ? (
            <Button
              variant="ghost"
              onClick={() => setShowAllEvents((value) => !value)}
              className={clsx("mt-5", focusRing)}
            >
              {showAllEvents ? "Show less" : "Show all"}
            </Button>
          ) : null}
        </section>

        <section aria-labelledby="decision-log-heading">
          <h2
            id="decision-log-heading"
            className="font-display text-2xl font-bold uppercase tracking-[0.12em] text-text-primary"
          >
            Decision log
          </h2>

          <div className="mt-6 overflow-x-auto border-2 border-navy bg-cream">
            <table
              aria-label="Memory-on decision log"
              className="w-full min-w-[820px] border-collapse text-left"
            >
              <thead>
                <tr>
                  <th scope="col" className={headCell}>
                    Round
                  </th>
                  <th scope="col" className={headCell}>
                    Agent
                  </th>
                  <th scope="col" className={clsx(headCell, "text-right")}>
                    Amount
                  </th>
                  <th scope="col" className={clsx(headCell, "text-right")}>
                    Formula limit
                  </th>
                  <th scope="col" className={clsx(headCell, "text-right")}>
                    Multiplier
                  </th>
                  <th scope="col" className={clsx(headCell, "text-right")}>
                    Final limit
                  </th>
                  <th scope="col" className={headCell}>
                    Decision
                  </th>
                </tr>
              </thead>
              <tbody>
                {onRows.map((row) => (
                  <tr
                    key={row.round}
                    className={clsx(
                      "border-b border-navy/20 last:border-b-0",
                      row.multiplier < 0.5 ? "bg-accent/40" : "",
                    )}
                  >
                    <td
                      className={clsx(
                        bodyCell,
                        "font-mono text-sm text-text-primary",
                      )}
                    >
                      {row.round}
                    </td>
                    <td
                      className={clsx(
                        bodyCell,
                        "font-mono text-xs text-text-primary",
                      )}
                    >
                      {row.agent}
                    </td>
                    <td
                      className={clsx(
                        bodyCell,
                        "text-right font-mono text-sm text-text-primary",
                      )}
                    >
                      {formatMoney(row.amount)}
                    </td>
                    <td
                      className={clsx(
                        bodyCell,
                        "text-right font-mono text-sm text-text-primary",
                      )}
                    >
                      {formatMoney(row.formula_limit)}
                    </td>
                    <td
                      className={clsx(
                        bodyCell,
                        "text-right font-mono text-sm text-text-primary",
                      )}
                    >
                      {formatMultiplier(row.multiplier)}
                    </td>
                    <td
                      className={clsx(
                        bodyCell,
                        "text-right font-mono text-sm text-text-primary",
                      )}
                    >
                      {formatMoney(row.final_limit)}
                    </td>
                    <td
                      className={clsx(
                        bodyCell,
                        "font-mono text-xs uppercase tracking-wider",
                        row.decision === "approved"
                          ? "text-navy"
                          : "text-maroon",
                      )}
                    >
                      {row.decision}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="mt-3 font-mono text-[10px] uppercase tracking-widest text-text-secondary">
            Yellow rows: multiplier below 0.5x.
          </p>
        </section>

        <section aria-labelledby="hidden-rule-heading">
          <h2
            id="hidden-rule-heading"
            className="font-display text-2xl font-bold uppercase tracking-[0.12em] text-text-primary"
          >
            Hidden rule
          </h2>

          <Button
            variant="secondary"
            onClick={() => setRuleRevealed(true)}
            disabled={ruleRevealed}
            className={clsx("mt-6", focusRing)}
          >
            Reveal
          </Button>

          {ruleRevealed ? (
            <Card tilt="left" className="mt-6 max-w-2xl">
              <p className="font-mono text-[10px] uppercase tracking-widest text-text-secondary">
                Ground truth
              </p>
              <p className="mt-3 text-sm leading-6 text-text-primary">
                {run.ground_truth.rule}
              </p>
              <p className="mt-5 font-display text-2xl font-bold leading-tight text-text-primary">
                Memory found it. The formula never could.
              </p>
            </Card>
          ) : null}
        </section>
      </div>
    </section>
  );
}
