import type { LoanCategory, Run, RunRow } from "@/lib/types";

const FORMULA_ONLY_RATIONALE = "Formula only (memory off).";

export interface AgentSummary {
  agent: string;
  principal: string;
  topCategory: LoanCategory;
  loansRequested: number;
  offDefaults: number;
  offLoss: number;
  onApprovals: number;
  onLoss: number;
  lossesAvoided: number;
}

export interface AgentTimelineRow {
  round: number;
  category: LoanCategory;
  amount: number;
  off: RunRow;
  on: RunRow;
}

export interface AgentMemory {
  round: number;
  rationale: string;
}

export type ResolvedRunRow = RunRow & {
  outcome: "repaid" | "defaulted";
};

function totalLoss(rows: RunRow[]): number {
  return rows.reduce((total, row) => total + row.loss, 0);
}

function mostUsedCategory(rows: RunRow[]): LoanCategory {
  const counts = new Map<LoanCategory, number>();

  for (const row of rows) {
    counts.set(row.category, (counts.get(row.category) ?? 0) + 1);
  }

  let best: LoanCategory = rows[0]?.category ?? "support-triage";
  let bestCount = -1;

  for (const [category, count] of counts) {
    if (count > bestCount || (count === bestCount && category < best)) {
      best = category;
      bestCount = count;
    }
  }

  return best;
}

export function getAgentNames(run: Run): string[] {
  return Array.from(
    new Set([...run.off, ...run.on].map((row) => row.agent)),
  ).sort();
}

export function buildAgentSummaries(run: Run): AgentSummary[] {
  const offByAgent = new Map<string, RunRow[]>();
  const onByAgent = new Map<string, RunRow[]>();

  for (const row of run.off) {
    const rows = offByAgent.get(row.agent) ?? [];
    rows.push(row);
    offByAgent.set(row.agent, rows);
  }

  for (const row of run.on) {
    const rows = onByAgent.get(row.agent) ?? [];
    rows.push(row);
    onByAgent.set(row.agent, rows);
  }

  return getAgentNames(run)
    .map((agent): AgentSummary => {
      const offRows = offByAgent.get(agent) ?? [];
      const onRows = onByAgent.get(agent) ?? [];
      const first = offRows[0] ?? onRows[0];
      const offLoss = totalLoss(offRows);
      const onLoss = totalLoss(onRows);

      return {
        agent,
        principal: first?.principal ?? "Unknown",
        topCategory: mostUsedCategory(offRows.length > 0 ? offRows : onRows),
        loansRequested: offRows.length,
        offDefaults: offRows.filter((row) => row.outcome === "defaulted")
          .length,
        offLoss,
        onApprovals: onRows.filter((row) => row.decision === "approved")
          .length,
        onLoss,
        lossesAvoided: offLoss - onLoss,
      };
    })
    .sort(
      (a, b) =>
        b.lossesAvoided - a.lossesAvoided || a.agent.localeCompare(b.agent),
    );
}

export function getAgentSummary(
  run: Run,
  agent: string,
): AgentSummary | undefined {
  return buildAgentSummaries(run).find((summary) => summary.agent === agent);
}

export function getAgentTimeline(run: Run, agent: string): AgentTimelineRow[] {
  const onByRound = new Map(run.on.map((row) => [row.round, row]));

  return run.off
    .filter((row) => row.agent === agent)
    .flatMap((off): AgentTimelineRow[] => {
      const on = onByRound.get(off.round);

      if (!on) {
        return [];
      }

      return [
        {
          round: off.round,
          category: off.category,
          amount: off.amount,
          off,
          on,
        },
      ];
    })
    .sort((a, b) => a.round - b.round);
}

export function getAgentMemories(run: Run, agent: string): AgentMemory[] {
  return run.on
    .filter(
      (row) =>
        row.agent === agent &&
        row.rationale.length > 0 &&
        row.rationale !== FORMULA_ONLY_RATIONALE,
    )
    .sort((a, b) => a.round - b.round)
    .map((row) => ({ round: row.round, rationale: row.rationale }));
}

export function getOnRows(run: Run): RunRow[] {
  return [...run.on].sort((a, b) => a.round - b.round);
}

export function isResolvedRow(row: RunRow): row is ResolvedRunRow {
  return row.outcome === "repaid" || row.outcome === "defaulted";
}

export function getRetainedOnRows(run: Run): ResolvedRunRow[] {
  return run.on.filter(isResolvedRow).sort((a, b) => b.round - a.round);
}
