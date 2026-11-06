import { clsx } from "clsx";
import type { CSSProperties, ReactNode } from "react";

export interface StickyNoteProps {
  children: ReactNode;
  rotationDeg?: number;
  className?: string;
}

export function StickyNote({
  children,
  rotationDeg,
  className,
}: StickyNoteProps) {
  const style: CSSProperties | undefined =
    rotationDeg === undefined ? undefined : { rotate: `${rotationDeg}deg` };

  return (
    <div
      style={style}
      className={clsx(
        "border-2 border-text-primary bg-accent p-4 shadow-[4px_4px_0px_rgba(31,36,42,1)] transition-transform duration-200 hover:scale-105",
        className,
      )}
    >
      {children}
    </div>
  );
}
