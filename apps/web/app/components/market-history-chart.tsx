'use client';

import { formatCoins } from '@/lib/format';
import type { BazaarHistoryPoint } from '@/lib/api';

const WIDTH = 720;
const HEIGHT = 230;
const PAD_X = 12;
const PAD_TOP = 14;
const PAD_BOTTOM = 22;

function dateLabel(value: string, compact = false) {
  const date = new Date(value);
  return date.toLocaleString([], compact ? { hour: '2-digit', minute: '2-digit' } : { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export function MarketHistoryChart({ points }: { points: BazaarHistoryPoint[] }) {
  if (points.length < 2) return <div className="chart-empty">Waiting for two retained observations</div>;

  const prices = points.flatMap((point) => [point.buy_low, point.buy_high, point.sell_low, point.sell_high]).filter((value) => value > 0);
  const rawMin = Math.min(...prices);
  const rawMax = Math.max(...prices);
  const padding = Math.max((rawMax - rawMin) * 0.08, rawMax * 0.01, 1);
  const min = Math.max(0, rawMin - padding);
  const max = rawMax + padding;
  const range = max - min || 1;
  const chartWidth = WIDTH - PAD_X * 2;
  const chartHeight = HEIGHT - PAD_TOP - PAD_BOTTOM;
  const x = (index: number) => PAD_X + (index / (points.length - 1)) * chartWidth;
  const y = (value: number) => PAD_TOP + ((max - value) / range) * chartHeight;
  const path = (values: number[]) => values.map((value, index) => `${index === 0 ? 'M' : 'L'} ${x(index).toFixed(2)} ${y(value).toFixed(2)}`).join(' ');
  const sellPath = path(points.map((point) => point.sell_close));
  const buyPath = path(points.map((point) => point.buy_close));
  const gridValues = [0, 0.25, 0.5, 0.75, 1].map((step) => max - step * (max - min));
  const latest = points[points.length - 1];

  return (
    <div className="history-chart-shell">
      <div className="history-chart-key">
        <span><i className="legend-green" /> Sell close</span>
        <span><i className="legend-blue" /> Buy close</span>
        <span className="history-samples">{points.reduce((sum, point) => sum + point.sample_count, 0).toLocaleString()} samples · {points.length} {points[points.length - 1].is_aggregated ? 'candles' : 'points'}</span>
      </div>
      <svg className="history-chart-svg" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Bazaar buy and sell price history">
        {gridValues.map((value) => <g key={value}><line className="history-grid-line" x1={PAD_X} x2={WIDTH - PAD_X} y1={y(value)} y2={y(value)} /><text className="history-axis-label" x={PAD_X} y={y(value) - 4}>{formatCoins(value)}</text></g>)}
        {points.map((point, index) => <line key={`${point.observed_at}-range`} className="history-range-line" x1={x(index)} x2={x(index)} y1={y(point.sell_high)} y2={y(point.sell_low)} />)}
        <path className="history-price-line history-sell-line" d={sellPath} />
        <path className="history-price-line history-buy-line" d={buyPath} />
        <circle className="history-last-dot history-sell-dot" cx={x(points.length - 1)} cy={y(latest.sell_close)} r="4" />
        <circle className="history-last-dot history-buy-dot" cx={x(points.length - 1)} cy={y(latest.buy_close)} r="4" />
      </svg>
      <div className="history-chart-axis"><span>{dateLabel(points[0].observed_at)}</span><span>{dateLabel(points[Math.floor((points.length - 1) / 2)].observed_at, true)}</span><span>{dateLabel(latest.observed_at)}</span></div>
      <div className="history-score-row" aria-label="Opportunity score history">
        <span className="history-score-label">SCORE</span>
        <div className="history-score-bars">{points.map((point) => <i key={point.observed_at} style={{ height: `${Math.max(4, Math.min(100, point.opportunity_score))}%` }} title={`${point.opportunity_score.toFixed(0)} score`} />)}</div>
      </div>
    </div>
  );
}
