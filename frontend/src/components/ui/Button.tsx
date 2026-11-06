import { clsx } from "clsx";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-text-primary text-[#F5F5F0] border-text-primary hover:bg-transparent hover:text-text-primary hover:shadow-[4px_4px_0px_rgba(27,23,34,1)]",
  secondary:
    "bg-transparent text-text-primary border-text-primary hover:bg-text-primary hover:text-[#F5F5F0]",
  ghost:
    "bg-transparent text-text-primary border-text-secondary/30 hover:border-text-primary",
  danger:
    "bg-danger text-cream border-danger hover:bg-transparent hover:text-danger",
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  icon?: ReactNode;
}

export function Button({
  variant = "primary",
  icon,
  className,
  children,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={clsx(
        "inline-flex items-center justify-center gap-3 border-2 px-8 py-3 font-mono text-sm font-bold uppercase tracking-widest transition-all duration-200 active:scale-[0.98] disabled:opacity-50",
        variantClasses[variant],
        className,
      )}
      {...props}
    >
      {icon}
      {children}
    </button>
  );
}
