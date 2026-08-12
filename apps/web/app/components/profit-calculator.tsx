'use client';

import { Calculator, RefreshCw } from 'lucide-react';
import { useState } from 'react';
import { optimizeCapital, type CapitalOptimizeResponse } from '@/lib/api';
import { formatCoins, formatDuration } from '@/lib/format';

export function ProfitCalculator() {
  const [capital, setCapital] = useState('100000');
  const [risk, setRisk] = useState<'conservative' | 'balanced' | 'aggressive'>('balanced');
  const [minimumRoi, setMinimumRoi] = useState('0');
  const [minimumLiquidity, setMinimumLiquidity] = useState('60');
  const [maxFill, setMaxFill] = useState('');
  const [maxFlips, setMaxFlips] = useState('5');
  const [result, setResult] = useState<CapitalOptimizeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const calculate = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const response = await optimizeCapital({
        available_capital: Number(capital),
        risk,
        minimum_roi: Number(minimumRoi || 0),
        minimum_liquidity: Number(minimumLiquidity || 0),
        maximum_concurrent_flips: Number(maxFlips || 5),
        ...(maxFill ? { max_fill_time_seconds: Number(maxFill) } : {}),
      });
      setResult(response);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Capital allocation could not be calculated.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="page-heading"><div><div className="eyebrow">CRAFTING TABLE / CAPITAL</div><h1>Profit calculator</h1><p>Build a conservative, balanced, or aggressive allocation from current qualified Bazaar signals.</p></div><div className="heading-actions"><span className="market-badge"><Calculator size={14} /> ESTIMATE ONLY</span></div></div>
      {error && <div className="alert-banner alert-error">{error}</div>}
      <section className="tool-layout"><form className="table-card tool-form" onSubmit={calculate}><div className="section-header"><div><div className="eyebrow">INPUTS</div><h2>Allocation rules</h2></div></div><label className="form-field"><span>Available capital</span><div className="input-with-unit"><input value={capital} onChange={(event) => setCapital(event.target.value)} type="number" min="1" step="1" required /><em>coins</em></div></label><label className="form-field"><span>Risk posture</span><select value={risk} onChange={(event) => setRisk(event.target.value as typeof risk)}><option value="conservative">Conservative</option><option value="balanced">Balanced</option><option value="aggressive">Aggressive</option></select></label><label className="form-field"><span>Minimum ROI</span><div className="input-with-unit"><input value={minimumRoi} onChange={(event) => setMinimumRoi(event.target.value)} type="number" min="0" step="0.1" /><em>%</em></div></label><label className="form-field"><span>Minimum liquidity</span><div className="input-with-unit"><input value={minimumLiquidity} onChange={(event) => setMinimumLiquidity(event.target.value)} type="number" min="0" max="100" step="1" /><em>/100</em></div></label><label className="form-field"><span>Maximum fill time</span><div className="input-with-unit"><input value={maxFill} onChange={(event) => setMaxFill(event.target.value)} type="number" min="1" step="1" placeholder="Any" /><em>seconds</em></div></label><label className="form-field"><span>Concurrent flips</span><input value={maxFlips} onChange={(event) => setMaxFlips(event.target.value)} type="number" min="1" max="50" step="1" required /></label><button className="primary-button form-submit" type="submit" disabled={loading}><RefreshCw size={14} /> {loading ? 'Calculating' : 'Calculate allocation'}</button><small className="muted-copy">This is an estimate from observed data. SkyFlip never places orders.</small></form><section className="table-card tool-result">{result ? <><div className="result-summary"><div><span>Projected net profit</span><strong className="positive">{formatCoins(result.projected_net_profit)}</strong></div><div><span>Allocated</span><strong>{formatCoins(result.available_capital - result.reserve)}</strong></div><div><span>Reserve</span><strong>{formatCoins(result.reserve)}</strong></div></div>{result.allocations.length ? <div className="result-table"><div className="result-table-head"><span>Instrument</span><span>Allocation</span><span>Profit</span><span>Fill</span></div>{result.allocations.map((allocation) => <div className="result-table-row" key={allocation.product_id}><span><strong>{allocation.product_name}</strong><small>{allocation.risk} · score {allocation.opportunity_score.toFixed(0)}</small></span><span className="number-cell">{formatCoins(allocation.allocation)}</span><span className="number-cell positive">{formatCoins(allocation.expected_net_profit)}</span><span>{formatDuration(allocation.estimated_fill_time_seconds)}</span></div>)}</div> : <div className="empty-state"><h3>No allocation matches these rules.</h3><p>Lower the liquidity or ROI thresholds, or increase available capital.</p></div>}</> : <div className="empty-state"><h3>Ready to calculate.</h3><p>Set your capital and constraints to rank the current live opportunities.</p></div>}</section></section>
    </>
  );
}
