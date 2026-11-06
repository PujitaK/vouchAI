import { clsx } from "clsx";
import type { ReactNode } from "react";

import { formatMoney, formatPercent } from "@/components/sim/format";
import type { Run, RunRow } from "@/lib/types";

function sumLoss(rows: RunRow[]) {
  return rows.reduce((total, row) => total + row.loss, 0);
}

function SummaryCell({
  label,
  children,
  className,
}: {
  label: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={clsx("p-4 sm:p-6", className)}>
      <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-secondary">
        {label}
      </p>
      <div className="mt-3">{children}</div>
    </div>
  );
}

export interface SummaryStripProps {
  run: Run;
  cursor: number;
}

export function SummaryStrip({ run, cursor }: SummaryStripProps) {
  const offRows = run.off.filter((row) => row.round <= cursor);
  const onRows = run.on.filter((row) => row.round <= cursor);

  const offLoss = sumLoss(offRows);
  const onLoss = sumLoss(onRows);
  const avoided = offLoss - onLoss;
  const avoidedPercent = offLoss > 0 ? (avoided / offLoss) * 100 : 0;

  const offApprovals = offRows.filter(
    (row) => row.decision === "approved",
  ).length;
  const onApprovals = onRows.filter(
    (row) => row.decision === "approved",
  ).length;

  return (
    <section
      aria-label="Run summary"
      className="grid grid-cols-2 border-2 border-navy bg-cream md:grid-cols-4"
    >
      <SummaryCell label="Loss off">
        <p className="font-mono text-3xl leading-none text-maroon sm:text-4xl">
          {formatMoney(offLoss)}
        </p>
      </SummaryCell>

      <SummaryCell
        label="Loss on"
        className="border-l-2 border-navy"
      >
        <p className="font-mono text-3xl leading-none text-[#017587] sm:text-4xl">
          {formatMoney(onLoss)}
        </p>
      </SummaryCell>

      <SummaryCell
        label="Losses avoided"
        className="border-t-2 border-navy md:border-l-2 md:border-t-0"
      >
        <p className="font-mono text-3xl leading-none text-text-primary sm:text-4xl">
          {formatMoney(avoided)}
        </p>
        <p className="mt-2 font-mono text-[10px] uppercase tracking-widest text-text-secondary">
          {formatPercent(avoidedPercent)} avoided
        </p>
      </SummaryCell>

      <SummaryCell
        label="Approvals on vs off"
        className="border-l-2 border-t-2 border-navy md:border-t-0"
      >
        <p className="font-mono text-3xl leading-none text-text-primary sm:text-4xl">
          {onApprovals} vs {offApprovals}
        </p>
      </SummaryCell>
    </section>
  );
}
