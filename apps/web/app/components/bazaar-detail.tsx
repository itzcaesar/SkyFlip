'use client';

import Link from 'next/link';
import { ArrowLeft, BarChart3, BookmarkPlus, Check, Clock3, Droplets, Info, ShieldCheck, TrendingUp } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { LiveEvents } from '@/app/components/live-events';
import { FreshnessBadge, RiskBadge, ScorePill } from '@/app/components/status-badge';
import { Sparkline } from '@/app/components/sparkline';
import { addWatchlist, getBazaarDetail, getBazaarHistory } from '@/lib/api';
import { formatCoins, formatDuration, formatPercent } from '@/lib/format';

export function BazaarDetail({ productId }: { productId: string }) {
  const [watchlistState, setWatchlistState] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const detail = useQuery({ queryKey: ['bazaar', 'detail', productId], queryFn: () => getBazaarDetail(productId), refetchInterval: 30_000 });
  const history = useQuery({ queryKey: ['bazaar', 'history', productId], queryFn: () => getBazaarHistory(productId), refetchInterval: 60_000, enabled: detail.isSuccess });
  const opportunity = detail.data?.opportunities.find((row) => row.flip_type === 'buy_order_to_sell_order') ?? detail.data?.opportunities[0];
  const points = history.data?.points ?? [];
  const addToWatchlist = async () => {
    setWatchlistState('saving');
    try {
      await addWatchlist({ product_id: productId, flip_type: opportunity?.flip_type ?? 'buy_order_to_sell_order', min_score: 70, min_profit: 0, min_roi: 0 });
      setWatchlistState('saved');
    } catch {
      setWatchlistState('error');
    }
  };

  return (
    <>
      <LiveEvents />
      <div className="back-row"><Link href="/bazaar"><ArrowLeft size={14} /> Back to screener</Link>{detail.data && <FreshnessBadge status={detail.data.freshness.status} message={detail.data.freshness.message} source={detail.data.freshness.source} />}</div>
      {detail.isLoading ? <div className="page-loading"><div className="loading-bar" /><div className="loading-grid"><div /><div /><div /></div><div className="loading-table" /></div> : detail.isError || !detail.data ? <div className="empty-state page-error"><h2>Product data is unavailable.</h2><p>{detail.error instanceof Error ? detail.error.message : 'This item has not been observed by the backend.'}</p></div> : <><div className="page-heading"><div><div className="eyebrow">BAZAAR / ITEM DETAIL</div><h1>{detail.data.product_name}</h1><p className="mono-text">{detail.data.product_id}</p></div><div className="heading-actions"><span className="market-badge">ORDER → SELL</span><button className="secondary-button" onClick={() => void addToWatchlist()} disabled={watchlistState === 'saving' || watchlistState === 'saved'}>{watchlistState === 'saved' ? <Check size={14} /> : <BookmarkPlus size={14} />} {watchlistState === 'saved' ? 'Watching' : watchlistState === 'saving' ? 'Saving' : 'Add to watchlist'}</button></div></div>{watchlistState === 'error' && <div className="alert-banner alert-error">Could not save this item to the local watchlist.</div>}{opportunity ? <><section className="detail-hero"><div className="hero-price"><span>Opportunity score</span><ScorePill score={opportunity.opportunity_score} classification={opportunity.classification} /><small>Explainable score; not a guarantee.</small></div><div className="hero-metric"><span>Net profit / unit</span><strong>{formatCoins(opportunity.net_profit)}</strong><small>{formatPercent(opportunity.roi)} ROI after configured fees</small></div><div className="hero-metric"><span>Capital / suggested cycle</span><strong>{formatCoins(opportunity.capital_required)}</strong><small>{opportunity.suggested_volume.toLocaleString()} units suggested</small></div><div className="hero-metric"><span>Risk / confidence</span><strong><RiskBadge risk={opportunity.manipulation_risk} /> <span className="confidence-number">{opportunity.confidence_score.toFixed(0)}%</span></strong><small>Confidence is data-dependent</small></div></section><section className="metric-grid"><Metric label="Entry / buy order" value={formatCoins(opportunity.buy_price)} icon={<TrendingUp size={15} />} /><Metric label="Exit / sell order" value={formatCoins(opportunity.sell_price)} icon={<BarChart3 size={15} />} /><Metric label="Visible volume" value={opportunity.transaction_volume.toLocaleString()} icon={<Droplets size={15} />} /><Metric label="Estimated fill" value={formatDuration(opportunity.estimated_fill_time_seconds)} icon={<Clock3 size={15} />} /><Metric label="Liquidity" value={`${opportunity.estimated_liquidity.toFixed(0)} / 100`} icon={<Droplets size={15} />} /><Metric label="Competition" value={`${opportunity.competition_score.toFixed(0)} / 100`} icon={<ShieldCheck size={15} />} /></section><div className="detail-columns"><section className="chart-card"><div className="card-heading"><div><div className="eyebrow">HISTORY</div><h2>Observed price & score</h2></div><span className="muted-label">{points.length} points</span></div><div className="chart-large"><Sparkline values={points.map((point) => point.sell_price)} color="#67e8a5" height={150} /></div><div className="chart-legend"><span><i className="legend-green" /> Sell price</span><span><i className="legend-blue" /> Score {opportunity.opportunity_score.toFixed(0)}</span></div></section><section className="signal-card"><div className="card-heading"><div><div className="eyebrow">SIGNAL LOGIC</div><h2>Why this signal moved</h2></div><Info size={16} /></div><ul className="signal-list">{opportunity.signal_explanations.map((explanation) => <li key={explanation}>{explanation}</li>)}</ul><div className="score-breakdown"><div className="eyebrow">SCORE BREAKDOWN</div>{Object.entries(opportunity.score_breakdown).map(([key, value]) => <div className="breakdown-row" key={key}><span>{key.replaceAll('_', ' ')}</span><strong>{typeof value === 'number' ? value.toFixed(1) : value}</strong></div>)}</div></section></div></> : <div className="empty-state"><h3>Price is not currently valid for an opportunity calculation.</h3><p>The backend received the product but did not invent missing prices or liquidity.</p></div>}</>}
    </>
  );
}

function Metric({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) { return <div className="metric-card"><div className="metric-icon">{icon}</div><span>{label}</span><strong>{value}</strong></div>; }
