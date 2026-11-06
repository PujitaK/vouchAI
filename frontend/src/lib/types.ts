export type RunMode = "real" | "fake";
export type LedgerMode = "off" | "on";
export type Decision = "approved" | "denied";
export type Outcome = "repaid" | "defaulted" | null;
export type LoanCategory =
  | "code-review"
  | "data-scraping"
  | "report-writing"
  | "support-triage";

export interface RunRow {
  round: number;
  agent: string;
  principal: string;
  category: LoanCategory;
  amount: number;
  formula_limit: number;
  multiplier: number;
  final_limit: number;
  decision: Decision;
  outcome: Outcome;
  loss: number;
  fee: number;
  cum_loss: number;
  cum_net: number;
  rationale: string;
  n_facts: number;
  latency_ms: number;
  would_default: boolean;
  mode: LedgerMode;
}

export interface GroundTruth {
  rule: string;
  novaops_data_scraping_default_probability: number;
  other_default_probability: number;
}

export interface Belief {
  after_round: number;
  text: string;
}

export interface ModeSummary {
  total_loss: number;
  net_pnl: number;
  approvals: number;
  denials: number;
  avg_latency_ms: number;
}

export interface RunSummary {
  off: ModeSummary;
  on: ModeSummary;
}

export interface Run {
  mode: RunMode;
  run_id: string;
  seed: number;
  rounds: number;
  ground_truth: GroundTruth;
  off: RunRow[];
  on: RunRow[];
  beliefs: Belief[];
  summary: RunSummary;
}

export type SimState = "idle" | "running" | "done" | "error";

export interface SimStatus {
  state: SimState;
  round: number;
  total: number;
  off: RunRow[];
  on: RunRow[];
  beliefs: Belief[];
  summary: RunSummary | null;
  error: string | null;
  run_id: string | null;
  mode: RunMode | null;
}
