import { clsx } from "clsx";
import type { ReactNode } from "react";

import { formatMoney, formatMultiplier } from "@/components/sim/format";
import { StatusDot } from "@/components/ui/StatusDot";
import { StickyNote } from "@/components/ui/StickyNote";
import type { Run, RunRow } from "@/lib/types";

function outcomeLabel(row: RunRow) {
  if (row.decision === "denied") {
    return "not lent";
  }

  return row.outcome ?? "pending";
}

function outcomeClass(row: RunRow) {
  if (row.outcome === "defaulted") {
    return "text-maroon";
  }

  if (row.outcome === "repaid") {
    return "text-[#017587]";
  }

  return "text-text-secondary";
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-secondary">
        {label}
      </dt>
      <dd className="mt-1 font-mono text-sm text-text-primary">{children}</dd>
    </div>
  );
}

function DecisionColumn({
  header,
  row,
  showMemory,
}: {
  header: string;
  row: RunRow;
  showMemory: boolean;
}) {
  return (
    <div className="min-w-0 p-4 sm:p-5">
      <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-secondary">
        {header}
      </p>

      <dl className="mt-4 space-y-3">
        <Field label="Agent">{row.agent}</Field>
        <Field label="Principal">{row.principal}</Field>
        <Field label="Category">{row.category}</Field>
        <Field label="Amount">{formatMoney(row.amount)}</Field>
        <Field label="Formula limit">{formatMoney(row.formula_limit)}</Field>

        {showMemory ? (
          <>
            <Field label="Multiplier">{formatMultiplier(row.multiplier)}</Field>
            <Field label="Final limit">{formatMoney(row.final_limit)}</Field>
          </>
        ) : null}

        <div>
          <dt className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-secondary">
            Decision
          </dt>
          <dd className="mt-2">
            <StatusDot status={row.decision} />
          </dd>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <dt className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-secondary">
              Outcome
            </dt>
            <dd
              className={clsx(
                "mt-1 font-mono text-sm",
                outcomeClass(row),
              )}
            >
              {outcomeLabel(row)}
            </dd>
          </div>
          <div>
            <dt className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-secondary">
              Loss
            </dt>
            <dd
              className={clsx(
                "mt-1 font-mono text-sm",
                row.loss > 0 ? "text-maroon" : "text-text-primary",
              )}
            >
              {formatMoney(row.loss)}
            </dd>
          </div>
        </div>
      </dl>

      {row.would_default && row.decision === "denied" ? (
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="border-2 border-maroon px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-maroon">
            Would have defaulted
          </span>
          <span className="font-mono text-[10px] uppercase tracking-widest text-maroon">
            Loss avoided
          </span>
        </div>
      ) : null}

      {showMemory && row.rationale ? (
        <StickyNote
          rotationDeg={-1.5}
          className="mt-5 text-sm leading-6 text-text-primary"
        >
          {row.rationale}
        </StickyNote>
      ) : null}
    </div>
  );
}

export interface RoundPanelProps {
  run: Run;
  cursor: number;
}

export function RoundPanel({ run, cursor }: RoundPanelProps) {
  const offRow = run.off.find((row) => row.round === cursor);
  const onRow = run.on.find((row) => row.round === cursor);

  return (
    <section className="min-w-0">
      <h2 className="mb-3 font-display text-xl font-bold tracking-tight text-text-primary">
        This round
      </h2>

      {offRow && onRow ? (
        <div className="border-2 border-navy bg-cream">
          <div className="border-b-2 border-navy px-4 py-2 sm:px-5">
            <p className="font-mono text-[10px] uppercase tracking-widest text-text-secondary">
              Round {cursor}
            </p>
          </div>
          <div className="grid grid-cols-2">
            <DecisionColumn header="Memory off" row={offRow} showMemory={false} />
            <div className="border-l-2 border-navy">
              <DecisionColumn header="Memory on" row={onRow} showMemory />
            </div>
          </div>
        </div>
      ) : (
        <div className="border-2 border-navy bg-cream p-5">
          <p className="font-mono text-sm uppercase tracking-widest text-text-secondary">
            No round selected.
          </p>
          <p className="mt-2 text-sm leading-6 text-text-secondary">
            Press Play or Restart to replay the ledger.
          </p>
        </div>
      )}
    </section>
  );
}
