'use client';

import Link from 'next/link';
import { ArrowUpRight, Search, Sparkles } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { FreshnessBadge, RiskBadge } from '@/app/components/status-badge';
import { formatCoins, formatPercent } from '@/lib/format';
import { getValuation, searchItems } from '@/lib/api';
import { useState } from 'react';

export function ItemValuator() {
  const [input, setInput] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const suggestions = useQuery({ queryKey: ['items', 'search', input], queryFn: () => searchItems(input), enabled: input.trim().length >= 2, staleTime: 30_000 });
  const valuation = useQuery({ queryKey: ['valuation', selected], queryFn: () => getValuation(selected as string), enabled: Boolean(selected), refetchInterval: 30_000 });

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const value = input.trim().toUpperCase();
    if (value) setSelected(value);
  };

  return (
    <>
      <div className="page-heading"><div><div className="eyebrow">CRAFTING TABLE / APPRAISAL</div><h1>Item valuator</h1><p>Estimate a Bazaar item’s current range from observed live prices and retained history.</p></div><div className="heading-actions"><span className="market-badge"><Sparkles size={14} /> EVIDENCE FIRST</span></div></div>
      <section className="table-card valuation-search"><form onSubmit={submit}><div className="filter-search"><Search size={15} /><input value={input} onChange={(event) => { setInput(event.target.value); setSelected(null); }} placeholder="Search item name or product ID" aria-label="Search item" /><button className="primary-button" type="submit">Value item</button></div></form>{suggestions.data?.items.length ? <div className="suggestion-list">{suggestions.data.items.slice(0, 8).map((item) => <button className="suggestion" key={item.id} onClick={() => { setInput(item.id); setSelected(item.id); }}><span className="item-icon">◇</span><span><strong>{item.name}</strong><small>{item.id}</small></span><ArrowUpRight size={14} /></button>)}</div> : null}</section>
      {valuation.isError && <div className="alert-banner alert-error">{valuation.error instanceof Error ? valuation.error.message : 'Valuation unavailable.'}</div>}
      {valuation.isLoading && <div className="table-card tool-loading">Reading observed item history…</div>}
      {valuation.data && <><div className="valuation-heading"><div><div className="eyebrow">OBSERVED ITEM</div><h2>{valuation.data.product_name}</h2><p className="mono-text">{valuation.data.product_id}</p></div><FreshnessBadge status={valuation.data.freshness.status} message={valuation.data.freshness.message} source={valuation.data.freshness.source} /></div><section className="valuation-grid"><ValueCard label="Current buy order" value={formatCoins(valuation.data.current_buy_order)} tone="green" /><ValueCard label="Current sell order" value={formatCoins(valuation.data.current_sell_order)} tone="blue" /><ValueCard label="Observed median" value={formatCoins(valuation.data.observed_median)} /><ValueCard label="Observed range" value={`${formatCoins(valuation.data.observed_low)} — ${formatCoins(valuation.data.observed_high)}`} /><ValueCard label="Price change" value={formatPercent(valuation.data.price_change_percent)} tone={valuation.data.price_change_percent != null && valuation.data.price_change_percent >= 0 ? 'green' : 'amber'} /><ValueCard label="Volatility" value={formatPercent(valuation.data.volatility_percent)} /><ValueCard label="Liquidity" value={valuation.data.liquidity != null ? `${valuation.data.liquidity.toFixed(0)} / 100` : '—'} /><ValueCard label="History points" value={valuation.data.history_points.toLocaleString()} /></section><div className="valuation-footer"><span>Confidence: {valuation.data.confidence != null ? `${valuation.data.confidence.toFixed(0)}%` : '—'}</span>{valuation.data.risk && <RiskBadge risk={valuation.data.risk} />}<Link className="secondary-button" href={`/bazaar/${encodeURIComponent(valuation.data.product_id)}`}>Open item detail <ArrowUpRight size={14} /></Link></div></>}
      {!valuation.data && !valuation.isLoading && !valuation.isError && <div className="table-card empty-state"><h3>Choose an item to begin.</h3><p>Search the live normalized item catalog, then compare current quotes with observed history.</p></div>}
    </>
  );
}

function ValueCard({ label, value, tone }: { label: string; value: string; tone?: 'green' | 'blue' | 'amber' }) {
  return <div className={`stat-tile ${tone ? `stat-${tone}` : ''}`}><div className="stat-top"><span>{label}</span></div><strong className="stat-value">{value}</strong></div>;
}
