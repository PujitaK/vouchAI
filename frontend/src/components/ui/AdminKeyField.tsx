"use client";

export interface AdminKeyFieldProps {
  value: string;
  onChange: (value: string) => void;
  hint?: string;
}

export function AdminKeyField({ value, onChange, hint }: AdminKeyFieldProps) {
  return (
    <div className="max-w-xl border-2 border-navy bg-cream p-4">
      <label
        htmlFor="admin-key"
        className="block font-mono text-xs uppercase tracking-widest text-text-secondary"
      >
        Admin key
      </label>
      <input
        id="admin-key"
        type="password"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        autoComplete="off"
        spellCheck={false}
        className="mt-2 block w-full border-2 border-navy bg-surface px-4 py-2 font-mono text-sm text-text-primary"
      />
      <p className="mt-2 font-mono text-[11px] text-text-secondary">
        {hint ?? "Stored in this browser tab only."}
      </p>
    </div>
  );
}
