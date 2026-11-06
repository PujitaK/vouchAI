export function formatMoney(value: number): string {
  const hasCents = Math.abs(value % 1) > 0.005;

  return value.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: hasCents ? 2 : 0,
    maximumFractionDigits: hasCents ? 2 : 0,
  });
}

export function formatPercent(value: number): string {
  return `${Math.round(value)}%`;
}

export function formatMultiplier(value: number): string {
  return `${value.toFixed(1)}x`;
}
