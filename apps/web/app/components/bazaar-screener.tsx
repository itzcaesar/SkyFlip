'use client';

import Link from 'next/link';
import { Filter, ListFilter, RefreshCw, Search, SlidersHorizontal } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { LiveEvents } from '@/app/components/live-events';
import { FreshnessBadge, RiskBadge, ScorePill } from '@/app/components/status-badge';
import { getBazaarPage, refreshBazaar } from '@/lib/api';
import { formatCoins, formatDuration, formatPercent } from '@/lib/format';

type Filters = { search: string; minProfit: string; minRoi: string; maxCapital: string; minVolume: string; minLiquidity: string; maxFillTime: string; minScore: string; minConfidence: string; flipType: 'buy_order_to_sell_order' | 'instant_buy_to_instant_sell'; sortBy: string; sortDir: 'asc' | 'desc' };
const defaultFilters: Filters = { search: '', minProfit: '', minRoi: '', maxCapital: '', minVolume: '', minLiquidity: '', maxFillTime: '', minScore: '55', minConfidence: '50', flipType: 'buy_order_to_sell_order', sortBy: 'opportunity_score', sortDir: 'desc' };

function fromInitialParams(initialParams: Record<string, string | string[] | undefined>): Filters {
  const value = (key: string) => {
    const entry = initialParams[key];
    return Array.isArray(entry) ? entry[0] ?? '' : entry ?? '';
  };
  return { ...defaultFilters, search: value('search'), minProfit: value('min_profit'), minRoi: value('min_roi'), maxCapital: value('max_capital'), minVolume: value('min_volume'), minLiquidity: value('min_liquidity'), maxFillTime: value('max_fill_time'), minScore: value('min_score') || defaultFilters.minScore, minConfidence: value('min_confidence') || defaultFilters.minConfidence, flipType: (value('flip_type') as Filters['flipType']) || defaultFilters.flipType, sortBy: value('sort_by') || defaultFilters.sortBy, sortDir: (value('sort_dir') as Filters['sortDir']) || defaultFilters.sortDir };
}

function toParams(filters: Filters) {
  const params = new URLSearchParams({ page: '1', page_size: '100', sort_by: filters.sortBy, sort_dir: filters.sortDir, flip_type: filters.flipType });
  const fields: Array<[keyof Filters, string]> = [['search', 'search'], ['minProfit', 'min_profit'], ['minRoi', 'min_roi'], ['maxCapital', 'max_capital'], ['minVolume', 'min_volume'], ['minLiquidity', 'min_liquidity'], ['maxFillTime', 'max_fill_time'], ['minScore', 'min_score'], ['minConfidence', 'min_confidence']];
  fields.forEach(([key, name]) => { if (filters[key]) params.set(name, filters[key] as string); });
  return params;
}

export function BazaarScreener({ initialParams = {} }: { initialParams?: Record<string, string | string[] | undefined> }) {
  const [filters, setFilters] = useState<Filters>(() => fromInitialParams(initialParams));
  const [showFilters, setShowFilters] = useState(true);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const params = useMemo(() => toParams(filters), [filters]);
  const query = useQuery({ queryKey: ['bazaar', 'screener', params.toString()], queryFn: () => getBazaarPage(params), refetchInterval: 30_000 });
  useEffect(() => { window.history.replaceState(null, '', `/bazaar?${params.toString()}`); }, [params]);
  const update = (key: keyof Filters, value: string) => setFilters((current) => ({ ...current, [key]: value }));
  const refreshNow = async () => {
    setRefreshError(null);
    try {
      await refreshBazaar();
      await query.refetch();
    } catch (error) {
      setRefreshError(error instanceof Error ? error.message : 'Latest Bazaar snapshot could not be fetched.');
    }
  };
  const sort = (column: string) => setFilters((current) => ({ ...current, sortBy: column, sortDir: current.sortBy === column && current.sortDir === 'desc' ? 'asc' : 'desc' }));
  const items = query.data?.items ?? [];

  return (
    <>
      <LiveEvents />
      <div className="page-heading"><div><div className="eyebrow">BAZAAR / SCREENER</div><h1>Find the spread</h1><p>Ranked by expected value, liquidity, confidence, and risk—not raw spread alone.</p></div><div className="heading-actions"><FreshnessBadge status={query.data?.freshness.status ?? (query.isLoading ? 'SYNCING' : 'UNAVAILABLE')} message={query.data?.freshness.message} /><button className="secondary-button" onClick={() => void refreshNow()} disabled={query.isFetching}><RefreshCw size={14} /> {query.isFetching ? 'Refreshing' : 'Refresh now'}</button></div></div>
      {query.data?.freshness.status === 'STALE' && <div className="alert-banner alert-warning"><RefreshCw size={16} /><span>Latest Bazaar snapshot is stale. Values remain visible for context, but are excluded from current signals.</span></div>}
      {query.isError && <div className="alert-banner alert-error"><span>{query.error instanceof Error ? query.error.message : 'Market data is temporarily unavailable.'}</span></div>}
      {refreshError && <div className="alert-banner alert-error"><span>{refreshError}</span></div>}

      <div className="screener-toolbar"><div className="tab-row"><button className={filters.flipType === 'buy_order_to_sell_order' ? 'tab-active' : ''} onClick={() => update('flipType', 'buy_order_to_sell_order')}>Buy order → sell order</button><button className={filters.flipType === 'instant_buy_to_instant_sell' ? 'tab-active' : ''} onClick={() => update('flipType', 'instant_buy_to_instant_sell')}>Instant buy → instant sell</button></div><button className="filter-toggle" onClick={() => setShowFilters((value) => !value)}><SlidersHorizontal size={14} /> Filters <span>{showFilters ? '−' : '+'}</span></button></div>
      {showFilters && <div className="filter-panel"><div className="filter-search"><Search size={15} /><input value={filters.search} onChange={(event) => update('search', event.target.value)} placeholder="Search item or product ID" /></div><div className="filter-field"><label>Min ROI</label><input value={filters.minRoi} onChange={(event) => update('minRoi', event.target.value)} inputMode="decimal" placeholder="0" /><span>%</span></div><div className="filter-field"><label>Min profit</label><input value={filters.minProfit} onChange={(event) => update('minProfit', event.target.value)} inputMode="decimal" placeholder="0" /><span>coins</span></div><div className="filter-field"><label>Max capital</label><input value={filters.maxCapital} onChange={(event) => update('maxCapital', event.target.value)} inputMode="decimal" placeholder="Any" /><span>coins</span></div><div className="filter-field"><label>Min liquidity</label><input value={filters.minLiquidity} onChange={(event) => update('minLiquidity', event.target.value)} inputMode="decimal" placeholder="0" /><span>/100</span></div><div className="filter-field"><label>Min score</label><input value={filters.minScore} onChange={(event) => update('minScore', event.target.value)} inputMode="decimal" placeholder="55" /><span>/100</span></div><button className="text-button" onClick={() => setFilters(defaultFilters)}><Filter size={14} /> Reset</button></div>}

      <div className="table-meta"><span><strong>{query.data?.total ?? '—'}</strong> observed opportunities</span><span className="meta-right"><ListFilter size={14} /> Click a column to sort</span></div>
      <section className="table-card data-table-card">
        {query.isLoading ? <div className="table-loading"><div className="skeleton-row" /><div className="skeleton-row" /><div className="skeleton-row" /><div className="skeleton-row" /></div> : items.length === 0 ? <div className="empty-state"><h3>{query.isError ? 'Market data is temporarily unavailable.' : 'No opportunities match these constraints.'}</h3><p>{query.isError ? 'The backend did not return a usable market snapshot.' : 'Try lowering the score or confidence threshold, or wait for the next real upstream update.'}</p></div> : <div className="table-scroll"><table><thead><tr><th>Instrument</th><th onClick={() => sort('buy_price')}>Entry</th><th onClick={() => sort('sell_price')}>Exit</th><th onClick={() => sort('net_profit')}>Net / unit</th><th onClick={() => sort('roi')}>ROI</th><th onClick={() => sort('transaction_volume')}>Volume</th><th onClick={() => sort('estimated_liquidity')}>Liquidity</th><th onClick={() => sort('confidence_score')}>Confidence</th><th onClick={() => sort('opportunity_score')}>Score</th><th>Risk</th></tr></thead><tbody>{items.map((item) => <tr key={`${item.product_id}-${item.flip_type}`}><td><Link className="item-link" href={`/bazaar/${encodeURIComponent(item.product_id)}`}><span className="item-icon">◇</span><span><strong>{item.product_name}</strong><small>{item.product_id}</small></span></Link></td><td className="number-cell">{formatCoins(item.buy_price)}</td><td className="number-cell">{formatCoins(item.sell_price)}</td><td className="number-cell positive">{formatCoins(item.net_profit)}</td><td className="number-cell">{formatPercent(item.roi)}</td><td className="number-cell">{item.transaction_volume.toLocaleString()}<small>{item.suggested_volume.toLocaleString()} suggested</small></td><td><div className="liquidity-cell"><span className="liquidity-track"><i style={{ width: `${Math.min(item.estimated_liquidity, 100)}%` }} /></span><span>{item.estimated_liquidity.toFixed(0)}</span></div></td><td className="number-cell">{item.confidence_score.toFixed(0)}%</td><td><ScorePill score={item.opportunity_score} classification={item.classification} /></td><td><RiskBadge risk={item.manipulation_risk} /><small className="table-subtext">{formatDuration(item.estimated_fill_time_seconds)}</small></td></tr>)}</tbody></table></div>}
      </section>
    </>
  );
}
