export function formatCoins(value: number | null | undefined, compact = true): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  if (!compact) return `${new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value)} coins`;
  const absolute = Math.abs(value);
  if (absolute >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`;
  if (absolute >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (absolute >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value);
}

export function formatPercent(value: number | null | undefined): string {
  return value === null || value === undefined || Number.isNaN(value) ? '—' : `${value.toFixed(2)}%`;
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return 'Unknown';
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}

