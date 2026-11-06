export default function Home() {
  return (
    <section className="relative py-10 sm:py-20">
      <div className="max-w-4xl">
        <p className="font-mono text-xs uppercase tracking-[0.35em] text-[#017587]">
          Underwriting ledger
        </p>
        <h1 className="mt-6 font-display text-5xl font-bold leading-[0.95] tracking-tight text-text-primary sm:text-7xl">
          Credit that learns.
        </h1>
        <div className="mt-8 h-2 w-24 bg-accent" aria-hidden="true" />
        <p className="mt-8 max-w-xl text-lg leading-8 text-text-secondary">
          A side-by-side record of formula underwriting and memory-led
          decisions.
        </p>
      </div>
    </section>
  );
}
