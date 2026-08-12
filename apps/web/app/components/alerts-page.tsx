'use client';

import Link from 'next/link';
import { Bell, CheckCheck, ExternalLink, RefreshCw, Trash2 } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { RiskBadge, ScorePill } from '@/app/components/status-badge';
import { formatCoins, formatPercent } from '@/lib/format';
import { getAlerts, getWatchlist, markAlertRead, markAllAlertsRead, removeWatchlist } from '@/lib/api';

export function AlertsPage() {
  const queryClient = useQueryClient();
  const alerts = useQuery({ queryKey: ['alerts'], queryFn: () => getAlerts(), refetchInterval: 30_000 });
  const watchlist = useQuery({ queryKey: ['watchlist'], queryFn: getWatchlist, refetchInterval: 30_000 });
  const read = useMutation({ mutationFn: markAlertRead, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['alerts'] }) });
  const readAll = useMutation({ mutationFn: markAllAlertsRead, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['alerts'] }) });
  const remove = useMutation({ mutationFn: removeWatchlist, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['watchlist'] }) });
  const unread = alerts.data?.filter((item) => !item.is_read).length ?? 0;

  return (
    <>
      <div className="page-heading">
        <div><div className="eyebrow">BAZAAR / ALERTS</div><h1>Signal watch</h1><p>Local watchlist alerts from the current live Bazaar snapshot.</p></div>
        <div className="heading-actions"><span className="market-badge">{unread} UNREAD</span><button className="secondary-button" onClick={() => { void queryClient.invalidateQueries({ queryKey: ['alerts'] }); void queryClient.invalidateQueries({ queryKey: ['watchlist'] }); }}><RefreshCw size={14} /> Refresh</button></div>
      </div>

      <section className="tool-section">
        <div className="section-header"><div><div className="eyebrow">WATCHLIST</div><h2>Tracked instruments</h2></div><span className="muted-label">LOCAL GUEST PROFILE</span></div>
        {watchlist.isLoading ? <div className="table-card tool-loading">Loading watchlist…</div> : watchlist.data?.length ? <div className="watchlist-grid">{watchlist.data.map((item) => <div className="watchlist-card" key={item.id}><div className="watchlist-card-top"><div><Link href={`/bazaar/${encodeURIComponent(item.product_id)}`} className="item-link"><span className="item-icon">◇</span><span><strong>{item.product_name}</strong><small>{item.product_id}</small></span></Link></div><button className="icon-button danger-button" aria-label={`Remove ${item.product_name}`} onClick={() => remove.mutate(item.id)} disabled={remove.isPending}><Trash2 size={15} /></button></div><div className="watchlist-thresholds"><span>Score ≥ {item.min_score.toFixed(0)}</span><span>Profit ≥ {formatCoins(item.min_profit)}</span><span>ROI ≥ {formatPercent(item.min_roi)}</span></div>{item.current_opportunity ? <div className="watchlist-current"><ScorePill score={item.current_opportunity.opportunity_score} classification={item.current_opportunity.classification} /><RiskBadge risk={item.current_opportunity.manipulation_risk} /><span>{formatCoins(item.current_opportunity.net_profit)} / unit</span></div> : <small className="muted-copy">Waiting for a fresh qualified signal.</small>}</div>)}</div> : <div className="table-card empty-state"><h3>Your watchlist is empty.</h3><p>Open a Bazaar item and press Add to watchlist to start receiving local alerts.</p><Link className="secondary-button empty-action-button" href="/bazaar">Open Bazaar</Link></div>}
      </section>

      <section className="tool-section section-header-spaced">
        <div className="section-header"><div><div className="eyebrow">EVENT LOG</div><h2>Recent alerts</h2></div><div className="heading-actions"><span className="muted-label">NO AUTOMATED TRADES</span>{unread > 0 && <button className="text-button" onClick={() => readAll.mutate()}><CheckCheck size={14} /> Mark all read</button>}</div></div>
        {alerts.isLoading ? <div className="table-card tool-loading">Scanning current alert log…</div> : alerts.data?.length ? <div className="table-card alert-list">{alerts.data.map((alert) => <div className={`alert-row ${alert.is_read ? 'alert-row-read' : ''}`} key={alert.id}><div className="alert-icon"><Bell size={15} /></div><div className="alert-copy"><div><strong>{alert.description}</strong><span className="alert-time">{new Date(alert.created_at).toLocaleString()}</span></div><div className="alert-meta"><span>{alert.item_key.split(':')[0]}</span><span>{alert.alert_type.replaceAll('_', ' ')}</span>{alert.risk && <RiskBadge risk={alert.risk} />}</div></div><div className="alert-actions">{alert.estimated_profit != null && <span className="positive number-cell">{formatCoins(alert.estimated_profit)}</span>}{!alert.is_read && <button className="secondary-button compact-button" onClick={() => read.mutate(alert.id)} disabled={read.isPending}>Read</button>}<Link className="icon-button" href={`/bazaar/${encodeURIComponent(alert.item_key.split(':')[0])}`} aria-label="Open item"><ExternalLink size={14} /></Link></div></div>)}</div> : <div className="table-card empty-state"><h3>No alerts yet.</h3><p>Alerts appear when a watched item crosses its score, profit, and ROI thresholds.</p></div>}
      </section>
    </>
  );
}
