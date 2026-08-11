'use client';

import Link from 'next/link';
import { ArrowUpRight, Gauge, Layers3, RefreshCw, TrendingUp, Waves } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { LiveEvents } from '@/app/components/live-events';
import { FreshnessBadge } from '@/app/components/status-badge';
import { StatTile } from '@/app/components/stat-tile';
import { getBazaarPage, getBazaarStatus, getHealth } from '@/lib/api';
import { formatCoins, formatPercent } from '@/lib/format';

export function Dashboard() {
  const status = useQuery({ queryKey: ['bazaar', 'status'], queryFn: getBazaarStatus, refetchInterval: 30_000 });
  const health = useQuery({ queryKey: ['health'], queryFn: getHealth, refetchInterval: 30_000 });
  const opportunities = useQuery({
    queryKey: ['bazaar', 'dashboard'],
    queryFn: () => getBazaarPage(new URLSearchParams({ page_size: '8', sort_by: 'opportunity_score', sort_dir: 'desc' })),
    refetchInterval: 30_000,
  });
  const top = opportunities.data?.items ?? [];
  const bestProfit = [...top].sort((a, b) => b.net_profit - a.net_profit)[0];
  const bestRoi = [...top].sort((a, b) => b.roi - a.roi)[0];
  const bestLiquidity = [...top].sort((a, b) => b.estimated_liquidity - a.estimated_liquidity)[0];
  const freshness = status.data?.freshness ?? opportunities.data?.freshness;

  return (
    <>
      <LiveEvents />
      <div className="page-heading">
        <div><div className="eyebrow">SESSION / OVERVIEW</div><h1>Market desk</h1><p>Evidence-first signals across the live Bazaar feed.</p></div>
        <div className="heading-actions"><FreshnessBadge status={freshness?.status ?? (status.isLoading ? 'SYNCING' : 'UNAVAILABLE')} message={freshness?.message} /><Link href="/bazaar" className="primary-button">Open screener <ArrowUpRight size={15} /></Link></div>
      </div>

      {status.isError && <div className="alert-banner alert-warning"><RefreshCw size={16} /><span>{status.error instanceof Error ? status.error.message : 'Market data is temporarily unavailable.'}</span></div>}

      <section className="market-strip">
        <div className="strip-label"><span className="status-pulse" /> GLOBAL MARKET STATUS</div>
        <div className="strip-stat"><span>API</span><strong>{freshness?.status === 'LIVE' ? 'CONNECTED' : freshness?.status ?? 'UNAVAILABLE'}</strong></div>
        <div className="strip-stat"><span>LAST UPDATE</span><strong>{freshness?.age_seconds != null ? `${freshness.age_seconds}s ago` : '—'}</strong></div>
        <div className="strip-stat"><span>QUALIFIED SIGNALS</span><strong>{status.data?.qualified_opportunities ?? '—'}</strong></div>
        <div className="strip-stat"><span>WORKER</span><strong className={health.data?.worker.status === 'ok' ? 'text-green' : ''}>{health.data?.worker.status === 'ok' ? 'RUNNING' : health.data?.worker.status?.toUpperCase() ?? 'CHECKING'}</strong></div>
      </section>

      <div className="section-header"><div><div className="eyebrow">BAZAAR / SNAPSHOT</div><h2>Signal summary</h2></div><span className="muted-label">ORDER → SELL STRATEGY</span></div>
      <section className="stat-grid">
        <StatTile label="Qualified opportunities" value={status.data ? status.data.qualified_opportunities.toLocaleString() : '—'} detail="Current, non-stale signals" tone="green" icon={<Gauge size={17} />} />
        <StatTile label="Highest net profit" value={bestProfit ? formatCoins(bestProfit.net_profit) : '—'} detail={bestProfit?.product_name ?? 'Waiting for live data'} tone="blue" icon={<TrendingUp size={17} />} />
        <StatTile label="Highest ROI" value={bestRoi ? formatPercent(bestRoi.roi) : '—'} detail={bestRoi?.product_name ?? 'Waiting for live data'} tone="amber" icon={<Waves size={17} />} />
        <StatTile label="Highest liquidity" value={bestLiquidity ? `${bestLiquidity.estimated_liquidity.toFixed(0)}/100` : '—'} detail={bestLiquidity?.product_name ?? 'Waiting for live data'} icon={<Layers3 size={17} />} />
      </section>

      <div className="section-header section-header-spaced"><div><div className="eyebrow">LIVE FEED</div><h2>Best observed signals</h2></div><span className="muted-label">NO SYNTHETIC EVENTS</span></div>
      <section className="table-card">
        {opportunities.isLoading ? <div className="table-loading">Loading the latest observed Bazaar snapshot…</div> : opportunities.isError ? <div className="empty-state"><h3>Market data is temporarily unavailable.</h3><p>Start the API and Bazaar worker, then refresh this view.</p></div> : top.length === 0 ? <div className="empty-state"><h3>No qualified signals yet.</h3><p>SkyFlip will show an empty state until the backend records real, sufficiently liquid market data.</p></div> : <div className="mini-signal-list">{top.slice(0, 5).map((item) => <Link className="mini-signal" href={`/bazaar/${encodeURIComponent(item.product_id)}`} key={`${item.product_id}-${item.flip_type}`}><div><strong>{item.product_name}</strong><span>{item.flip_type === 'buy_order_to_sell_order' ? 'Order → sell' : 'Instant → instant'}</span></div><div className="mini-signal-metric"><span>{formatCoins(item.net_profit)} / unit</span><strong>{item.opportunity_score.toFixed(0)}</strong></div><ArrowUpRight size={15} /></Link>)}</div>}
      </section>
    </>
  );
}
