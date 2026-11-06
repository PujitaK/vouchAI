import { clsx } from "clsx";
import fs from "node:fs";
import path from "node:path";
import { notFound } from "next/navigation";

import { formatMoney } from "@/components/sim/format";
import { Card } from "@/components/ui/Card";
import { StatusDot } from "@/components/ui/StatusDot";
import { StickyNote } from "@/components/ui/StickyNote";
import {
  getAgentMemories,
  getAgentNames,
  getAgentSummary,
  getAgentTimeline,
} from "@/lib/aggregate";
import type { Run, RunRow } from "@/lib/types";

const rotations = [-2, 1.5, -1];

const headCell =
  "border-b-2 border-navy bg-surface px-3 py-3 font-mono text-[10px] uppercase tracking-[0.18em] text-text-secondary";

const bodyCell = "border-b border-navy/20 px-3 py-3";

function readRun(): Run {
  const filePath = path.join(process.cwd(), "public", "cached_run.json");

  return JSON.parse(fs.readFileSync(filePath, "utf8")) as Run;
}

function outcomeLabel(row: RunRow): string {
  if (row.decision === "denied") {
    return "not lent";
  }

  return row.outcome ?? "pending";
}

function outcomeClass(row: RunRow): string {
  if (row.outcome === "defaulted") {
    return "text-maroon";
  }

  if (row.outcome === "repaid") {
    return "text-[#017587]";
  }

  return "text-text-secondary";
}

export function generateStaticParams() {
  return getAgentNames(readRun()).map((name) => ({ name }));
}

export default async function AgentDetailPage({
  params,
}: {
  params: Promise<{ name: string }>;
}) {
  const { name } = await params;
  const run = readRun();
  const summary = getAgentSummary(run, name);

  if (!summary) {
    notFound();
  }

  const timeline = getAgentTimeline(run, name);
  const memories = getAgentMemories(run, name);
  const agentStatus = summary.offDefaults > 0 ? "defaulted" : "repaid";

  return (
    <section className="py-8">
      <header className="mb-10 max-w-4xl">
        <p className="font-mono text-xs uppercase tracking-[0.35em] text-[#017587]">
          Agent ledger
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-3">
          <h1 className="font-display text-4xl font-bold tracking-tight text-text-primary sm:text-5xl">
            {summary.agent}
          </h1>
          <StatusDot
            status={agentStatus}
            pulse={agentStatus === "defaulted"}
          />
        </div>
        <p className="mt-3 font-mono text-sm uppercase tracking-[0.2em] text-text-secondary">
          {summary.principal}
        </p>
      </header>

      <div className="grid gap-12 lg:grid-cols-[minmax(0,1.55fr)_minmax(0,0.75fr)] lg:items-start">
        <section className="min-w-0">
          <h2 className="font-display text-xl font-bold tracking-tight text-text-primary">
            Loan timeline
          </h2>

          <div className="mt-4 overflow-x-auto border-2 border-navy bg-cream">
            <table
              aria-label={`Loan timeline for ${summary.agent}`}
              className="w-full min-w-[880px] border-collapse text-left"
            >
              <thead>
                <tr>
                  <th scope="col" className={headCell}>
                    Round
                  </th>
                  <th scope="col" className={headCell}>
                    Category
                  </th>
                  <th scope="col" className={clsx(headCell, "text-right")}>
                    Amount
                  </th>
                  <th scope="col" className={headCell}>
                    OFF decision
                  </th>
                  <th scope="col" className={headCell}>
                    OFF outcome
                  </th>
                  <th scope="col" className={clsx(headCell, "text-right")}>
                    OFF loss
                  </th>
                  <th scope="col" className={headCell}>
                    ON decision
                  </th>
                  <th scope="col" className={headCell}>
                    ON outcome
                  </th>
                  <th scope="col" className={clsx(headCell, "text-right")}>
                    ON loss
                  </th>
                </tr>
              </thead>
              <tbody>
                {timeline.map((row) => (
                  <tr
                    key={row.round}
                    className="border-b border-navy/20 last:border-b-0"
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
                        "font-mono text-xs text-text-secondary",
                      )}
                    >
                      {row.category}
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
                        "font-mono text-xs uppercase tracking-wider",
                        row.off.decision === "approved"
                          ? "text-navy"
                          : "text-maroon",
                      )}
                    >
                      {row.off.decision}
                    </td>
                    <td
                      className={clsx(
                        bodyCell,
                        "font-mono text-xs",
                        outcomeClass(row.off),
                      )}
                    >
                      {outcomeLabel(row.off)}
                    </td>
                    <td
                      className={clsx(
                        bodyCell,
                        "text-right font-mono text-sm",
                        row.off.loss > 0
                          ? "text-maroon"
                          : "text-text-primary",
                      )}
                    >
                      {formatMoney(row.off.loss)}
                    </td>
                    <td
                      className={clsx(
                        bodyCell,
                        "font-mono text-xs uppercase tracking-wider",
                        row.on.decision === "approved"
                          ? "text-navy"
                          : "text-maroon",
                      )}
                    >
                      {row.on.decision}
                    </td>
                    <td
                      className={clsx(
                        bodyCell,
                        "font-mono text-xs",
                        outcomeClass(row.on),
                      )}
                    >
                      {outcomeLabel(row.on)}
                    </td>
                    <td
                      className={clsx(
                        bodyCell,
                        "text-right font-mono text-sm",
                        row.on.loss > 0
                          ? "text-maroon"
                          : "text-text-primary",
                      )}
                    >
                      {formatMoney(row.on.loss)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="min-w-0">
          <h2 className="font-display text-xl font-bold uppercase tracking-[0.12em] text-text-primary">
            What memory said
          </h2>

          {memories.length > 0 ? (
            <div className="mt-4 space-y-5">
              {memories.map((memory, index) => (
                <StickyNote
                  key={memory.round}
                  rotationDeg={rotations[index % rotations.length]}
                  className="text-sm leading-6 text-text-primary"
                >
                  <p className="font-mono text-[10px] uppercase tracking-widest text-text-secondary">
                    Round {memory.round}
                  </p>
                  <p className="mt-2 whitespace-pre-line">
                    {memory.rationale}
                  </p>
                </StickyNote>
              ))}
            </div>
          ) : (
            <Card tilt="left" className="mt-4">
              <p className="font-mono text-xs uppercase tracking-widest text-text-secondary">
                No memory notes
              </p>
              <p className="mt-3 text-sm leading-6 text-text-primary">
                This agent has no non-formula memory notes in the run.
              </p>
            </Card>
          )}
        </section>
      </div>
    </section>
  );
}
