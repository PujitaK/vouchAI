"use client";

import { clsx } from "clsx";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { formatMoney } from "@/components/sim/format";
import { Card } from "@/components/ui/Card";
import { buildAgentSummaries } from "@/lib/aggregate";
import { useRun } from "@/lib/useRun";

const linkFocus =
  "focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-[-2px] focus-visible:outline-accent";

const headCell =
  "border-b-2 border-navy bg-surface px-3 py-3 font-mono text-[10px] uppercase tracking-[0.18em] text-text-secondary";

const bodyCell = "border-b border-navy/20 px-3 py-3";

export default function AgentsPage() {
  const { run, loading, error } = useRun();
  const router = useRouter();

  if (loading) {
    return (
      <div className="py-16 font-mono text-xs uppercase tracking-[0.2em] text-text-secondary">
        Loading agent ledger...
      </div>
    );
  }

  if (!run) {
    return (
      <Card tilt="left" className="max-w-xl">
        <p className="font-mono text-xs uppercase tracking-widest text-text-secondary">
          Agent ledger unavailable
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

  const agents = buildAgentSummaries(run);

  return (
    <section className="py-8">
      <header className="mb-10 max-w-3xl">
        <p className="font-mono text-xs uppercase tracking-[0.35em] text-[#017587]">
          Agent ledger
        </p>
        <h1 className="mt-4 font-display text-4xl font-bold tracking-tight text-text-primary sm:text-5xl">
          Agents
        </h1>
        <p className="mt-5 text-lg leading-8 text-text-secondary">
          Twelve agents. Healthy on paper. Not all of them are.
        </p>
      </header>

      {agents.length > 0 ? (
        <div className="overflow-x-auto border-2 border-navy bg-cream">
          <table
            aria-label="Agent ledger"
            className="w-full min-w-[980px] border-collapse text-left"
          >
            <thead>
              <tr>
                <th scope="col" className={headCell}>
                  Agent
                </th>
                <th scope="col" className={headCell}>
                  Principal
                </th>
                <th scope="col" className={headCell}>
                  Category
                </th>
                <th scope="col" className={clsx(headCell, "text-right")}>
                  Loans requested
                </th>
                <th scope="col" className={clsx(headCell, "text-right")}>
                  OFF defaults
                </th>
                <th scope="col" className={clsx(headCell, "text-right")}>
                  OFF loss
                </th>
                <th scope="col" className={clsx(headCell, "text-right")}>
                  ON approved
                </th>
                <th scope="col" className={clsx(headCell, "text-right")}>
                  ON loss
                </th>
                <th scope="col" className={clsx(headCell, "text-right")}>
                  Losses avoided
                </th>
              </tr>
            </thead>
            <tbody>
              {agents.map((agent) => {
                const href = `/agents/${encodeURIComponent(agent.agent)}`;
                const hasAvoidedLosses = agent.lossesAvoided > 0;

                return (
                  <tr
                    key={agent.agent}
                    onClick={() => router.push(href)}
                    className="cursor-pointer border-b border-navy/20 transition-colors last:border-b-0 hover:bg-surface/60"
                  >
                    <td
                      className={clsx(
                        bodyCell,
                        "border-l-4",
                        hasAvoidedLosses
                          ? "border-accent"
                          : "border-transparent",
                      )}
                    >
                      <Link
                        href={href}
                        onClick={(event) => event.stopPropagation()}
                        className={clsx(
                          "font-mono text-sm text-text-primary underline decoration-2 underline-offset-4",
                          linkFocus,
                        )}
                      >
                        {agent.agent}
                      </Link>
                    </td>
                    <td
                      className={clsx(
                        bodyCell,
                        "font-mono text-sm text-text-primary",
                      )}
                    >
                      {agent.principal}
                    </td>
                    <td
                      className={clsx(
                        bodyCell,
                        "font-mono text-xs text-text-secondary",
                      )}
                    >
                      {agent.topCategory}
                    </td>
                    <td
                      className={clsx(
                        bodyCell,
                        "text-right font-mono text-sm text-text-primary",
                      )}
                    >
                      {agent.loansRequested}
                    </td>
                    <td
                      className={clsx(
                        bodyCell,
                        "text-right font-mono text-sm",
                        agent.offDefaults > 0
                          ? "text-maroon"
                          : "text-text-primary",
                      )}
                    >
                      {agent.offDefaults}
                    </td>
                    <td
                      className={clsx(
                        bodyCell,
                        "text-right font-mono text-sm",
                        agent.offLoss > 0
                          ? "text-maroon"
                          : "text-text-primary",
                      )}
                    >
                      {formatMoney(agent.offLoss)}
                    </td>
                    <td
                      className={clsx(
                        bodyCell,
                        "text-right font-mono text-sm text-text-primary",
                      )}
                    >
                      {agent.onApprovals}
                    </td>
                    <td
                      className={clsx(
                        bodyCell,
                        "text-right font-mono text-sm",
                        agent.onLoss > 0
                          ? "text-maroon"
                          : "text-text-primary",
                      )}
                    >
                      {formatMoney(agent.onLoss)}
                    </td>
                    <td
                      className={clsx(
                        bodyCell,
                        "text-right font-mono text-sm",
                        hasAvoidedLosses
                          ? "text-text-primary"
                          : "text-text-secondary",
                      )}
                    >
                      {formatMoney(agent.lossesAvoided)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <Card tilt="left" className="max-w-xl">
          <p className="font-mono text-xs uppercase tracking-widest text-text-secondary">
            No agents found
          </p>
          <p className="mt-3 text-sm leading-6 text-text-primary">
            The run does not contain any agent rows.
          </p>
        </Card>
      )}
    </section>
  );
}
