import { Card } from "./Card";

export function LiveModeNotice() {
  return (
    <div className="py-8">
      <Card>
        <h1 className="font-display text-3xl font-bold tracking-tight text-text-primary">
          Live mode
        </h1>
        <p className="mt-4 text-sm leading-6 text-text-secondary">
          Live mode runs against the backend. Watch the demo video, or run it locally (see README).
        </p>
      </Card>
    </div>
  );
}
