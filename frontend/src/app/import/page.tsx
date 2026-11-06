"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

interface RejectedRow {
  line: number;
  reason: string;
}

interface ImportResult {
  added: number;
  rejected: RejectedRow[];
  total: number;
}

export default function ImportPage() {
  const [kind, setKind] = useState<"tasks" | "loans">("tasks");
  const [file, setFile] = useState<File | null>(null);
  const [replace, setReplace] = useState(false);
  const [teachMemory, setTeachMemory] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);

  const apiUrl = (
    process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000"
  ).replace(/\/+$/, "");
  const adminKey = process.env.NEXT_PUBLIC_ADMIN_KEY;

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("Please choose a CSV file to upload.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);

    const params = new URLSearchParams();
    if (kind === "tasks" && replace) {
      params.append("replace", "true");
    }
    if (kind === "loans" && !teachMemory) {
      params.append("teach_memory", "false");
    }

    const query = params.toString() ? `?${params.toString()}` : "";
    const headers: Record<string, string> = {};
    if (adminKey) {
      headers["X-API-Key"] = adminKey;
    }

    try {
      const response = await fetch(`${apiUrl}/import/${kind}${query}`, {
        method: "POST",
        headers,
        body: formData,
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? `Upload failed (${response.status})`);
      }

      setResult(data as ImportResult);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "An unexpected error occurred."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="py-8 space-y-10">
      <header className="max-w-2xl">
        <p className="font-mono text-xs uppercase tracking-[0.35em] text-[#017587]">
          Data Ingestion
        </p>
        <h1 className="mt-3 font-display text-4xl font-bold tracking-tight text-text-primary sm:text-5xl">
          Import CSV Records
        </h1>
        <p className="mt-4 text-sm leading-6 text-text-secondary">
          Upload historical agent task executions or resolved loans. VouchAI automatically
          identifies agents and principals, guards against identity conflicts, and updates
          underwriting records.
        </p>
      </header>

      <div className="grid gap-8 lg:grid-cols-2">
        <form
          onSubmit={handleUpload}
          className="border-2 border-navy bg-cream p-8 space-y-6"
        >
          <div>
            <label className="block font-mono text-xs uppercase tracking-widest text-text-secondary">
              Record Type
            </label>
            <div className="mt-3 flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer font-mono text-sm">
                <input
                  type="radio"
                  name="kind"
                  value="tasks"
                  checked={kind === "tasks"}
                  onChange={() => {
                    setKind("tasks");
                    setResult(null);
                  }}
                  className="accent-navy"
                />
                Tasks (tasks.csv)
              </label>
              <label className="flex items-center gap-2 cursor-pointer font-mono text-sm">
                <input
                  type="radio"
                  name="kind"
                  value="loans"
                  checked={kind === "loans"}
                  onChange={() => {
                    setKind("loans");
                    setResult(null);
                  }}
                  className="accent-navy"
                />
                Loans (loans.csv)
              </label>
            </div>
          </div>

          <div>
            <label className="block font-mono text-xs uppercase tracking-widest text-text-secondary">
              CSV File
            </label>
            <input
              type="file"
              accept=".csv"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="mt-3 block w-full border-2 border-navy bg-surface px-4 py-2 font-mono text-xs text-text-primary file:mr-4 file:border-0 file:bg-navy file:px-3 file:py-1 file:font-mono file:text-xs file:text-cream hover:file:bg-navy/80"
            />
            <p className="mt-2 font-mono text-[11px] text-text-secondary">
              Max file size 2 MB. UTF-8 encoded.
            </p>
          </div>

          {kind === "tasks" ? (
            <label className="flex items-center gap-2 cursor-pointer font-mono text-xs text-text-secondary">
              <input
                type="checkbox"
                checked={replace}
                onChange={(e) => setReplace(e.target.checked)}
                className="accent-navy"
              />
              Replace existing database records (local dev use only)
            </label>
          ) : (
            <label className="flex items-center gap-2 cursor-pointer font-mono text-xs text-text-secondary">
              <input
                type="checkbox"
                checked={teachMemory}
                onChange={(e) => setTeachMemory(e.target.checked)}
                className="accent-navy"
              />
              Teach Hindsight memory with imported loan outcomes
            </label>
          )}

          <Button
            type="submit"
            disabled={loading || !file}
            className="w-full"
          >
            {loading ? "Importing..." : `Upload & Process ${kind}`}
          </Button>

          {error && (
            <div className="border border-maroon bg-maroon/10 p-4 font-mono text-xs text-maroon">
              {error}
            </div>
          )}
        </form>

        <div className="space-y-6">
          <Card tilt="right">
            <h2 className="font-mono text-xs uppercase tracking-widest text-text-secondary">
              Expected CSV Columns
            </h2>
            {kind === "tasks" ? (
              <div className="mt-4 font-mono text-xs text-text-primary space-y-2">
                <p className="font-bold text-navy">
                  agent, principal, category, success, amount, [ts]
                </p>
                <ul className="list-disc pl-5 space-y-1 text-text-secondary text-[11px]">
                  <li><strong className="text-text-primary">agent:</strong> Agent identifier</li>
                  <li><strong className="text-text-primary">principal:</strong> Fleet owner name</li>
                  <li><strong className="text-text-primary">category:</strong> Work category (e.g. data-scraping)</li>
                  <li><strong className="text-text-primary">success:</strong> true or false</li>
                  <li><strong className="text-text-primary">amount:</strong> Numeric value &gt; 0</li>
                  <li><strong className="text-text-primary">ts:</strong> Optional ISO-8601 timestamp</li>
                </ul>
              </div>
            ) : (
              <div className="mt-4 font-mono text-xs text-text-primary space-y-2">
                <p className="font-bold text-navy">
                  agent, principal, category, amount, outcome
                </p>
                <ul className="list-disc pl-5 space-y-1 text-text-secondary text-[11px]">
                  <li><strong className="text-text-primary">agent:</strong> Agent identifier</li>
                  <li><strong className="text-text-primary">principal:</strong> Fleet owner name</li>
                  <li><strong className="text-text-primary">category:</strong> Loan purpose category</li>
                  <li><strong className="text-text-primary">amount:</strong> Credit amount &gt; 0</li>
                  <li><strong className="text-text-primary">outcome:</strong> repaid or defaulted</li>
                </ul>
              </div>
            )}
          </Card>

          {result && (
            <div className="border-2 border-navy bg-surface p-6 space-y-4">
              <h2 className="font-display text-lg font-bold text-text-primary">
                Import Summary
              </h2>
              <div className="grid grid-cols-3 gap-3 font-mono text-center">
                <div className="border border-navy/20 bg-cream p-3">
                  <div className="text-2xl font-bold text-[#017587]">
                    {result.added}
                  </div>
                  <div className="text-[10px] uppercase tracking-wider text-text-secondary">
                    Added
                  </div>
                </div>
                <div className="border border-navy/20 bg-cream p-3">
                  <div className="text-2xl font-bold text-maroon">
                    {result.rejected.length}
                  </div>
                  <div className="text-[10px] uppercase tracking-wider text-text-secondary">
                    Rejected
                  </div>
                </div>
                <div className="border border-navy/20 bg-cream p-3">
                  <div className="text-2xl font-bold text-text-primary">
                    {result.total}
                  </div>
                  <div className="text-[10px] uppercase tracking-wider text-text-secondary">
                    Total Rows
                  </div>
                </div>
              </div>

              {result.rejected.length > 0 && (
                <div className="space-y-2">
                  <p className="font-mono text-xs font-bold text-maroon uppercase tracking-wider">
                    Rejected Rows:
                  </p>
                  <div className="max-h-60 overflow-y-auto border border-navy/20 bg-cream">
                    <table className="w-full text-left font-mono text-xs">
                      <thead className="border-b border-navy/20 bg-surface">
                        <tr>
                          <th className="px-3 py-2 text-text-secondary w-16">Line</th>
                          <th className="px-3 py-2 text-text-secondary">Reason</th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.rejected.map((r, i) => (
                          <tr key={i} className="border-b border-navy/10 last:border-0">
                            <td className="px-3 py-2 font-bold text-text-primary">
                              #{r.line}
                            </td>
                            <td className="px-3 py-2 text-maroon">{r.reason}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
