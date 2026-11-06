import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "VouchAI | Credit that learns",
  description:
    "A ledger of formula underwriting and memory-led credit decisions.",
};

const navItems = [
  { href: "/", label: "Simulation" },
  { href: "/agents", label: "Agents" },
  { href: "/loans", label: "Live Loan" },
  { href: "/import", label: "Import" },
  { href: "/memory", label: "Memory" },
];

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">
        <header className="sticky top-0 z-50 border-b-2 border-navy bg-cream">
          <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-6 py-5 sm:flex-row sm:items-end sm:justify-between">
            <Link href="/" className="group inline-flex flex-col self-start">
              <span className="font-display text-2xl font-bold tracking-tight text-text-primary">
                VouchAI
              </span>
              <span
                className="mt-1 h-1.5 w-10 bg-accent transition-all duration-200 group-hover:w-16"
                aria-hidden="true"
              />
            </Link>
            <nav
              aria-label="Primary"
              className="flex flex-wrap items-center gap-2 sm:gap-4"
            >
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="hover-sweep inline-block px-2 py-1 font-mono text-xs uppercase tracking-widest text-text-primary"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        <main className="mx-auto w-full max-w-6xl px-6 py-12 sm:py-16">
          {children}
        </main>
      </body>
    </html>
  );
}
