import { clsx } from "clsx";

export type DotStatus =
  | "approved"
  | "denied"
  | "repaid"
  | "defaulted"
  | "idle";

const dotClasses: Record<DotStatus, string> = {
  approved: "bg-navy",
  denied: "bg-maroon",
  repaid: "bg-base",
  defaulted: "bg-maroon",
  idle: "bg-gray-400",
};

export interface StatusDotProps {
  status: DotStatus;
  label?: string;
  pulse?: boolean;
  className?: string;
}

export function StatusDot({
  status,
  label,
  pulse = false,
  className,
}: StatusDotProps) {
  const shouldPulse = pulse && status === "defaulted";

  return (
    <span className={clsx("inline-flex items-center gap-2", className)}>
      <span className="relative flex h-2 w-2" aria-hidden="true">
        {shouldPulse ? (
          <span className="absolute inline-flex h-full w-full animate-ping bg-maroon opacity-75" />
        ) : null}
        <span className={clsx("relative h-2 w-2", dotClasses[status])} />
      </span>
      <span className="font-mono text-xs uppercase tracking-wider text-text-secondary">
        {label ?? status}
      </span>
    </span>
  );
}
