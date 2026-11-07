"use client";

import { useEffect, useState } from "react";
import { formatMoney } from "@/components/sim/format";
import { AdminKeyField } from "@/components/ui/AdminKeyField";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { LiveModeNotice } from "@/components/ui/LiveModeNotice";
import { StatusDot, type DotStatus } from "@/components/ui/StatusDot";
import { StickyNote } from "@/components/ui/StickyNote";
import { useAdminKey } from "@/lib/useAdminKey";

interface AgentSummary {
  id: number;
  name: string;
  principal: string;
  category: string;
  score: number;
  confidence: number;
  formula_limit: number;
}

interface LoanOut {
  id: number;
  agent_id: number;
  agent_name?: string;
  requested_amount: number;
  formula_limit: number;
  final_limit: number;
  multiplier: number;
  decision: string;
  rationale: string;
  status: string;
  identity_blocked: boolean;
  memory_used: boolean;
  memory_facts: string[];
  memory_latency_ms?: number;
  llm_latency_ms?: number;
  total_latency_ms?: number;
  created_at: string;
  resolved_at?: string;
}

function getDotStatus(status: string): DotStatus {
  if (status === "defaulted") return "defaulted";
  if (status === "repaid") return "repaid";
  if (status === "denied") return "denied";
  if (status === "approved" || status === "active") return "approved";
  return "idle";
}

const WAKE_MESSAGE =
  "Waking the server (free hosting sleeps when idle). Retrying...";
const WAKE_TIMEOUT_MS = 8000;
const WAKE_RETRIES = 4;
const WAKE_DELAY_MS = 10000;
const RETRYABLE_STATUSES = new Set([502, 503, 504]);

export default function LiveLoanPage() {
  if (!process.env.NEXT_PUBLIC_API_URL) {
    return <LiveModeNotice />;
  }

  return <LiveLoanContent />;
}

function LiveLoanContent() {
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<number | null>(null);
  const [amount, setAmount] = useState<number>(200);
  const [purpose, setPurpose] = useState<string>("API cluster execution and data indexing");
  const [useMemory, setUseMemory] = useState<boolean>(true);

  const [loading, setLoading] = useState(false);
  const [waking, setWaking] = useState(false);
  const [resolving, setResolving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loan, setLoan] = useState<LoanOut | null>(null);
  const [resolutionMessage, setResolutionMessage] = useState<string | null>(null);

  const apiUrl = (
    process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000"
  ).replace(/\/+$/, "");
  const { adminKey, setAdminKey } = useAdminKey();

  useEffect(() => {
    async function loadAgents() {
      try {
        const res = await fetch(`${apiUrl}/agents`);
        if (!res.ok) throw new Error("Failed to load agents");
        const data: AgentSummary[] = await res.json();
        setAgents(data);
        setSelectedAgentId((current) => current ?? data[0]?.id ?? null);
      } catch (err: unknown) {
        setError(
          err instanceof Error
            ? `Could not reach backend API at ${apiUrl}: ${err.message}`
            : "Failed to connect to backend"
        );
      }
    }
    void loadAgents();
  }, [apiUrl]);

  const selectedAgent = agents.find((a) => a.id === selectedAgentId);

  async function fetchWithWakeRetry(
    url: string,
    init: RequestInit
  ): Promise<Response> {
    let lastError: unknown = null;
    let lastStatus: number | null = null;

    for (let attempt = 0; attempt <= WAKE_RETRIES; attempt += 1) {
      const controller = new AbortController();
      const timeout = window.setTimeout(
        () => controller.abort(),
        WAKE_TIMEOUT_MS
      );

      try {
        const res = await fetch(url, { ...init, signal: controller.signal });
        window.clearTimeout(timeout);

        if (!RETRYABLE_STATUSES.has(res.status)) {
          return res;
        }

        lastStatus = res.status;
        lastError = null;
      } catch (err: unknown) {
        window.clearTimeout(timeout);
        lastError = err;
        lastStatus = null;
      }

      if (attempt < WAKE_RETRIES) {
        setWaking(true);
        await new Promise((resolve) =>
          window.setTimeout(resolve, WAKE_DELAY_MS)
        );
      }
    }

    if (lastError instanceof Error) {
      throw lastError;
    }
    if (lastStatus !== null) {
      throw new Error(
        `Backend returned ${lastStatus} after retries. Please try again.`
      );
    }
    throw new Error("Could not reach the backend after retries");
  }

  async function handleApply(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedAgentId) return;

    setLoading(true);
    setWaking(false);
    setError(null);
    setLoan(null);
    setResolutionMessage(null);

    try {
      const res = await fetchWithWakeRetry(`${apiUrl}/loans/${selectedAgentId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          amount,
          purpose,
          use_memory: useMemory,
          bank_id: "vouchai-lender-main",
        }),
      });

      setWaking(false);
      setError(null);

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail ?? `Request failed (${res.status})`);
      }

      setLoan(data as LoanOut);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Error processing loan application"
      );
    } finally {
      setWaking(false);
      setLoading(false);
    }
  }

  async function handleResolve(outcome: "repaid" | "defaulted") {
    if (!loan) return;

    const trimmedKey = adminKey.trim();
    if (!trimmedKey) {
      setError("Enter the admin key to resolve loans");
      return;
    }

    setResolving(true);
    setError(null);
    setResolutionMessage(null);

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "X-API-Key": trimmedKey,
    };

    try {
      const res = await fetch(`${apiUrl}/loans/${loan.id}/resolve`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          outcome,
          bank_id: "vouchai-lender-main",
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail ?? `Resolution failed (${res.status})`);
      }

      setLoan(data as LoanOut);
      setResolutionMessage(
        `Loan #${loan.id} resolved as ${outcome.toUpperCase()}. Outcome retained to Hindsight memory.`
      );
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Error resolving loan"
      );
    } finally {
      setResolving(false);
    }
  }

  return (
    <div className="py-8 space-y-10">
      <AdminKeyField
        value={adminKey}
        onChange={setAdminKey}
        hint="Required to resolve loans. Stored in this browser tab only."
      />

      <header className="max-w-3xl">
        <p className="font-mono text-xs uppercase tracking-[0.35em] text-[#017587]">
          Real-Time Origination
        </p>
        <h1 className="mt-3 font-display text-4xl font-bold tracking-tight text-text-primary sm:text-5xl">
          Live Loan Underwriting
        </h1>
        <p className="mt-4 text-sm leading-6 text-text-secondary">
          Request a real-time loan for any agent. Watch the pipeline execute: identity security gate, formula credit baseline, Hindsight memory recall, and LLM underwriting decision.
        </p>
      </header>

      <div className="grid gap-8 lg:grid-cols-2">
        <form
          onSubmit={handleApply}
          className="border-2 border-navy bg-cream p-8 space-y-6"
        >
          <div>
            <label className="block font-mono text-xs uppercase tracking-widest text-text-secondary">
              Select Applicant Agent
            </label>
            <select
              value={selectedAgentId ?? ""}
              onChange={(e) => setSelectedAgentId(Number(e.target.value))}
              className="mt-2 block w-full border-2 border-navy bg-surface px-4 py-2 font-mono text-sm text-text-primary"
            >
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} ({a.principal} &middot; {a.category}) &mdash; Formula Limit: ${a.formula_limit}
                </option>
              ))}
            </select>
          </div>

          {selectedAgent && (
            <div className="border border-navy/20 bg-surface p-4 text-xs font-mono grid grid-cols-2 gap-2">
              <div>
                <span className="text-text-secondary">Principal: </span>
                <strong className="text-text-primary">{selectedAgent.principal}</strong>
              </div>
              <div>
                <span className="text-text-secondary">Category: </span>
                <strong className="text-text-primary">{selectedAgent.category}</strong>
              </div>
              <div>
                <span className="text-text-secondary">Credit Score: </span>
                <strong className="text-text-primary">{selectedAgent.score.toFixed(1)}/100</strong>
              </div>
              <div>
                <span className="text-text-secondary">Confidence: </span>
                <strong className="text-text-primary">{(selectedAgent.confidence * 100).toFixed(0)}%</strong>
              </div>
            </div>
          )}

          <div>
            <label className="block font-mono text-xs uppercase tracking-widest text-text-secondary">
              Requested Amount ($)
            </label>
            <input
              type="number"
              min={10}
              max={5000}
              step={10}
              value={amount}
              onChange={(e) => setAmount(Number(e.target.value))}
              required
              className="mt-2 block w-full border-2 border-navy bg-surface px-4 py-2 font-mono text-sm text-text-primary"
            />
          </div>

          <div>
            <label className="block font-mono text-xs uppercase tracking-widest text-text-secondary">
              Purpose / Task Context
            </label>
            <input
              type="text"
              value={purpose}
              onChange={(e) => setPurpose(e.target.value)}
              required
              className="mt-2 block w-full border-2 border-navy bg-surface px-4 py-2 font-mono text-sm text-text-primary"
            />
          </div>

          <label className="flex items-center gap-2 cursor-pointer font-mono text-xs text-text-secondary">
            <input
              type="checkbox"
              checked={useMemory}
              onChange={(e) => setUseMemory(e.target.checked)}
              className="accent-navy"
            />
            Recall past fleet patterns from Hindsight memory
          </label>

          <Button
            type="submit"
            disabled={loading || !selectedAgentId}
            className="w-full"
          >
            {loading
              ? waking
                ? "Waking Server..."
                : "Evaluating Application..."
              : "Submit Loan Request"}
          </Button>

          {waking && (
            <div className="border border-[#b7791f] bg-[#fef3c7] p-4 font-mono text-xs text-[#7b341e]">
              {WAKE_MESSAGE}
            </div>
          )}

          {error && !waking && (
            <div className="border border-maroon bg-maroon/10 p-4 font-mono text-xs text-maroon">
              {error}
            </div>
          )}
        </form>

        <div className="space-y-6">
          {loan ? (
            <div className="space-y-6">
              {loan.identity_blocked ? (
                <div className="border-2 border-maroon bg-maroon/10 p-6 space-y-3">
                  <div className="flex items-center gap-3">
                    <span className="h-3 w-3 rounded-full bg-maroon" />
                    <h2 className="font-mono text-sm font-bold uppercase tracking-wider text-maroon">
                      Identity Gate Triggered &mdash; Application Blocked
                    </h2>
                  </div>
                  <p className="font-mono text-xs text-text-primary leading-5">
                    {loan.rationale}
                  </p>
                  <p className="font-mono text-[11px] text-text-secondary">
                    Formula scoring, memory recall, and LLM underwriting were bypassed for security.
                  </p>
                </div>
              ) : (
                <div className="border-2 border-[#017587] bg-[#017587]/10 p-4 font-mono text-xs text-[#017587] flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-[#017587]" />
                  Identity Gate Passed: Agent verified under principal &apos;{selectedAgent?.principal}&apos;.
                </div>
              )}

              <div className="border-2 border-navy bg-cream p-6 space-y-6">
                <div className="flex items-center justify-between border-b border-navy/20 pb-4">
                  <div>
                    <span className="font-mono text-[10px] uppercase tracking-widest text-text-secondary">
                      Loan #{loan.id} Decision
                    </span>
                    <h3 className="font-display text-2xl font-bold uppercase tracking-wide">
                      <span className={loan.decision === "approved" ? "text-[#017587]" : "text-maroon"}>
                        {loan.decision}
                      </span>
                    </h3>
                  </div>
                  <div className="text-right">
                    <span className="font-mono text-[10px] uppercase tracking-widest text-text-secondary">
                      Status
                    </span>
                    <div className="flex items-center justify-end gap-2 mt-1">
                      <StatusDot status={getDotStatus(loan.status)} />
                      <span className="font-mono text-xs uppercase font-bold text-text-primary">
                        {loan.status}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3 font-mono text-center">
                  <div className="border border-navy/20 bg-surface p-3">
                    <div className="text-lg font-bold text-text-primary">
                      {formatMoney(loan.formula_limit)}
                    </div>
                    <div className="text-[10px] uppercase tracking-wider text-text-secondary">
                      Formula Limit
                    </div>
                  </div>
                  <div className="border border-navy/20 bg-surface p-3">
                    <div className="text-lg font-bold text-navy">
                      {loan.multiplier.toFixed(2)}x
                    </div>
                    <div className="text-[10px] uppercase tracking-wider text-text-secondary">
                      Multiplier
                    </div>
                  </div>
                  <div className="border border-navy/20 bg-surface p-3">
                    <div className="text-lg font-bold text-[#017587]">
                      {formatMoney(loan.final_limit)}
                    </div>
                    <div className="text-[10px] uppercase tracking-wider text-text-secondary">
                      Final Limit
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="font-mono text-xs uppercase tracking-widest text-text-secondary">
                    Underwriting Rationale
                  </h4>
                  <p className="mt-2 font-mono text-xs text-text-primary bg-surface p-3 border border-navy/20 leading-5">
                    {loan.rationale}
                  </p>
                </div>

                {loan.memory_facts && loan.memory_facts.length > 0 && (
                  <div>
                    <h4 className="font-mono text-xs uppercase tracking-widest text-text-secondary">
                      Recalled Hindsight Facts ({loan.memory_facts.length})
                    </h4>
                    <div className="mt-3 space-y-2">
                      {loan.memory_facts.map((fact, idx) => (
                        <StickyNote key={idx} rotationDeg={idx % 2 === 0 ? 1 : -1} className="text-xs font-mono">
                          {fact}
                        </StickyNote>
                      ))}
                    </div>
                  </div>
                )}

                {loan.status === "active" && (
                  <div className="border-t border-navy/20 pt-5 space-y-3">
                    <h4 className="font-mono text-xs uppercase tracking-widest text-text-secondary">
                      Resolve Loan Outcome (Live Retain)
                    </h4>
                    <p className="font-mono text-[11px] text-text-secondary">
                      Mark outcome to test whether Hindsight retains this lesson for future rounds:
                    </p>
                    <div className="grid grid-cols-2 gap-4">
                      <Button
                        variant="secondary"
                        disabled={resolving}
                        onClick={() => handleResolve("repaid")}
                        className="text-xs"
                      >
                        {resolving ? "Resolving..." : "Repaid in Full"}
                      </Button>
                      <Button
                        variant="danger"
                        disabled={resolving}
                        onClick={() => handleResolve("defaulted")}
                        className="text-xs"
                      >
                        {resolving ? "Resolving..." : "Mark as Defaulted"}
                      </Button>
                    </div>
                  </div>
                )}

                {resolutionMessage && (
                  <div className="border border-[#017587] bg-[#017587]/10 p-3 font-mono text-xs text-[#017587]">
                    {resolutionMessage}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <Card tilt="right">
              <h3 className="font-mono text-xs uppercase tracking-widest text-text-secondary">
                Pipeline Awaiting Submission
              </h3>
              <p className="mt-3 text-sm leading-6 text-text-primary">
                Select an agent on the left and submit a loan request.
              </p>
              <ul className="mt-4 space-y-2 font-mono text-xs text-text-secondary list-disc pl-5">
                <li>Evaluates name lookalikes &amp; name-washing identity gate.</li>
                <li>Queries Hindsight memory for fleet default records.</li>
                <li>Blends reputation formula limit with memory multiplier.</li>
                <li>Allows immediate resolution to simulate retain/recall feedback loop.</li>
              </ul>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
