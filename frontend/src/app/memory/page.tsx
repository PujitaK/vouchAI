import { Card } from "@/components/ui/Card";

export default function MemoryPage() {
  return (
    <section className="py-8">
      <div className="mb-10 max-w-2xl">
        <p className="font-mono text-xs uppercase tracking-[0.35em] text-[#017587]">
          Memory journal
        </p>
        <h1 className="mt-4 font-display text-4xl font-bold tracking-tight text-text-primary sm:text-5xl">
          Memory
        </h1>
      </div>
      <Card tilt="right" className="max-w-xl">
        <p className="font-mono text-xs uppercase tracking-widest text-text-secondary">
          Coming next
        </p>
        <h2 className="mt-3 font-display text-2xl font-bold text-text-primary">
          The memory journal is coming next.
        </h2>
        <p className="mt-3 leading-7 text-text-secondary">
          Recalled facts and periodic beliefs from the underwriter will live
          here.
        </p>
      </Card>
    </section>
  );
}
