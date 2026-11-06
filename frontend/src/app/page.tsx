"use client";

import { SimulationView } from "@/components/sim/SimulationView";
import { Card } from "@/components/ui/Card";
import { useRun } from "@/lib/useRun";

export default function Home() {
  const { run, loading, error } = useRun();

  if (loading) {
    return (
      <div className="py-16 font-mono text-xs uppercase tracking-[0.2em] text-text-secondary">
        LOADING LEDGER...
      </div>
    );
  }

  if (!run) {
    return (
      <Card tilt="left" className="max-w-xl">
        <p className="font-mono text-xs uppercase tracking-widest text-text-secondary">
          Run unavailable
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

  return <SimulationView key={run.run_id} run={run} />;
}
