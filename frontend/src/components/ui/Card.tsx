import { clsx } from "clsx";
import type { ReactNode } from "react";

type CardTilt = "left" | "right" | "none";

const tiltClasses: Record<CardTilt, string> = {
  left: "-rotate-1",
  right: "rotate-1",
  none: "-rotate-[0.5deg]",
};

export interface CardProps {
  children: ReactNode;
  tilt?: CardTilt;
  className?: string;
}

export function Card({ children, tilt = "none", className }: CardProps) {
  return (
    <div
      className={clsx(
        "relative bg-[#FDF3C8] p-8 shadow-[4px_4px_12px_rgba(0,0,0,0.08)]",
        tiltClasses[tilt],
        className,
      )}
    >
      <div className="flex items-center justify-between" aria-hidden="true">
        {["one", "two", "three", "four"].map((mark) => (
          <span key={mark} className="h-[10px] w-[10px] bg-gray-300/80" />
        ))}
      </div>
      <div className="mt-4">{children}</div>
    </div>
  );
}
