import { describe, expect, it } from 'vitest';
import { formatCoins, formatDuration, formatPercent } from './format';

describe('market formatting', () => {
  it('formats SkyBlock coin magnitudes compactly', () => {
    expect(formatCoins(1_250)).toBe('1.3K');
    expect(formatCoins(12_500_000)).toBe('12.50M');
    expect(formatCoins(1_250_000_000)).toBe('1.25B');
  });

  it('does not invent values for unavailable metrics', () => {
    expect(formatCoins(null)).toBe('—');
    expect(formatPercent(undefined)).toBe('—');
    expect(formatDuration(null)).toBe('Unknown');
  });
});

