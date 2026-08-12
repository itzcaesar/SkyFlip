'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { Bell, CheckCheck, ExternalLink, Monitor, Pencil, RefreshCw, Save, Trash2, X } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { RiskBadge, ScorePill } from '@/app/components/status-badge';
import { formatCoins, formatPercent } from '@/lib/format';
import { getAlertPreferences, getAlerts, getWatchlist, markAlertRead, markAllAlertsRead, removeWatchlist, updateAlertPreferences, updateWatchlist, type WatchlistItem } from '@/lib/api';

type WatchlistDraft = { min_score: string; min_profit: string; min_roi: string };

function draftFrom(item: WatchlistItem): WatchlistDraft {
  return { min_score: String(item.min_score), min_profit: String(item.min_profit), min_roi: String(item.min_roi) };
}

export function AlertsPage() {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<number | null>(null);
  const [draft, setDraft] = useState<WatchlistDraft | null>(null);
  const [cooldown, setCooldown] = useState('5');
  const firstAlertLoad = useRef(true);
  const knownAlertIds = useRef(new Set<number>());
  const alerts = useQuery({ queryKey: ['alerts'], queryFn: () => getAlerts(), refetchInterval: 30_000 });
  const watchlist = useQuery({ queryKey: ['watchlist'], queryFn: () => getWatchlist(true), refetchInterval: 30_000 });
  const preferences = useQuery({ queryKey: ['alert-preferences'], queryFn: getAlertPreferences });
  const read = useMutation({ mutationFn: markAlertRead, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['alerts'] }) });
  const readAll = useMutation({ mutationFn: markAllAlertsRead, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['alerts'] }) });
  const remove = useMutation({ mutationFn: removeWatchlist, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['watchlist'] }) });
  const saveWatchlist = useMutation({ mutationFn: ({ id, payload }: { id: number; payload: WatchlistDraft }) => updateWatchlist(id, { min_score: Number(payload.min_score), min_profit: Number(payload.min_profit), min_roi: Number(payload.min_roi) }), onSuccess: () => { setEditing(null); setDraft(null); void queryClient.invalidateQueries({ queryKey: ['watchlist'] }); } });
  const toggleWatchlist = useMutation({ mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) => updateWatchlist(id, { is_active }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['watchlist'] }) });
  const savePreferences = useMutation({ mutationFn: updateAlertPreferences, onSuccess: (data) => { setCooldown(String(data.cooldown_minutes)); void queryClient.invalidateQueries({ queryKey: ['alert-preferences'] }); } });
  const unread = alerts.data?.filter((item) => !item.is_read).length ?? 0;

  useEffect(() => {
    if (!alerts.data) return;
    const currentIds = new Set(alerts.data.map((alert) => alert.id));
    if (firstAlertLoad.current) {
      firstAlertLoad.current = false;
      knownAlertIds.current = currentIds;
      return;
    }
    if (preferences.data?.browser_notifications && 'Notification' in window && Notification.permission === 'granted') {
      alerts.data.filter((alert) => !knownAlertIds.current.has(alert.id) && !alert.is_read).forEach((alert) => new Notification('SkyFlip watchlist alert', { body: alert.description }));
    }
    knownAlertIds.current = currentIds;
  }, [alerts.data, preferences.data?.browser_notifications]);

  function beginEdit(item: WatchlistItem) {
    setEditing(item.id);
    setDraft(draftFrom(item));
  }

  async function enableBrowserNotifications() {
    if (!('Notification' in window)) return;
    const permission = await Notification.requestPermission();
    if (permission === 'granted') savePreferences.mutate({ browser_notifications: true });
  }

  return (
    <>
      <div className="page-heading">
        <div><div className="eyebrow">BAZAAR / ALERTS</div><h1>Signal watch</h1><p>Local thresholds and browser delivery for the current live Bazaar snapshot.</p></div>
        <div className="heading-actions"><span className="market-badge">{unread} UNREAD</span><button className="secondary-button" onClick={() => { void queryClient.invalidateQueries({ queryKey: ['alerts'] }); void queryClient.invalidateQueries({ queryKey: ['watchlist'] }); }}><RefreshCw size={14} /> Refresh</button></div>
      </div>

      <section className="tool-section table-card alert-preferences">
        <div className="section-header"><div><div className="eyebrow">DELIVERY SETTINGS</div><h2>Local notifications</h2></div><span className="muted-label">NO EXTERNAL CHANNELS</span></div>
        <div className="alert-preferences-grid">
          <label className="preference-toggle"><input type="checkbox" checked={preferences.data?.enabled ?? true} onChange={(event) => savePreferences.mutate({ enabled: event.target.checked })} /><span><strong>Alert generation</strong><small>Keep creating watchlist events in the local event log.</small></span></label>
          <label className="form-field"><span>Minimum severity</span><select value={preferences.data?.minimum_severity ?? 'MEDIUM'} onChange={(event) => savePreferences.mutate({ minimum_severity: event.target.value as 'LOW' | 'MEDIUM' | 'HIGH' })}><option value="LOW">LOW and above</option><option value="MEDIUM">MEDIUM and above</option><option value="HIGH">HIGH only</option></select></label>
          <label className="form-field"><span>Cooldown</span><div className="input-with-unit"><input type="number" min="1" max="1440" value={cooldown} onChange={(event) => setCooldown(event.target.value)} onBlur={() => savePreferences.mutate({ cooldown_minutes: Number(cooldown) || 5 })} /><em>minutes</em></div></label>
          <div className="browser-notification-setting"><div className="preference-icon"><Monitor size={15} /></div><div><strong>Browser notifications</strong><small>{preferences.data?.browser_notifications ? 'Enabled for this browser.' : 'Optional desktop notifications for new events.'}</small></div><button className="secondary-button compact-button" onClick={() => preferences.data?.browser_notifications ? savePreferences.mutate({ browser_notifications: false }) : void enableBrowserNotifications()}>{preferences.data?.browser_notifications ? 'Disable' : 'Enable'}</button></div>
        </div>
      </section>

      <section className="tool-section">
        <div className="section-header"><div><div className="eyebrow">WATCHLIST</div><h2>Tracked instruments</h2></div><span className="muted-label">EDITABLE PER ITEM</span></div>
        {watchlist.isLoading ? <div className="table-card tool-loading">Loading watchlist…</div> : watchlist.data?.length ? <div className="watchlist-grid">{watchlist.data.map((item) => <div className={`watchlist-card ${item.is_active ? '' : 'watchlist-card-inactive'}`} key={item.id}><div className="watchlist-card-top"><div><Link href={`/bazaar/${encodeURIComponent(item.product_id)}`} className="item-link"><span className="item-icon">◇</span><span><strong>{item.product_name}</strong><small>{item.product_id} · {item.is_active ? 'ACTIVE' : 'PAUSED'}</small></span></Link></div><div className="watchlist-card-actions"><button className="icon-button" aria-label={`Edit ${item.product_name}`} onClick={() => beginEdit(item)}><Pencil size={14} /></button><button className="icon-button danger-button" aria-label={`Remove ${item.product_name}`} onClick={() => remove.mutate(item.id)} disabled={remove.isPending}><Trash2 size={15} /></button></div></div>{editing === item.id && draft ? <form className="watchlist-edit" onSubmit={(event) => { event.preventDefault(); saveWatchlist.mutate({ id: item.id, payload: draft }); }}><label className="form-field"><span>Minimum score</span><input type="number" min="0" max="100" value={draft.min_score} onChange={(event) => setDraft({ ...draft, min_score: event.target.value })} /></label><label className="form-field"><span>Minimum profit</span><div className="input-with-unit"><input type="number" min="0" value={draft.min_profit} onChange={(event) => setDraft({ ...draft, min_profit: event.target.value })} /><em>coins</em></div></label><label className="form-field"><span>Minimum ROI</span><div className="input-with-unit"><input type="number" min="0" value={draft.min_roi} onChange={(event) => setDraft({ ...draft, min_roi: event.target.value })} /><em>%</em></div></label><div className="form-actions"><button className="primary-button compact-button" type="submit" disabled={saveWatchlist.isPending}><Save size={13} /> Save</button><button className="secondary-button compact-button" type="button" onClick={() => { setEditing(null); setDraft(null); }}><X size={13} /> Cancel</button></div></form> : <><div className="watchlist-thresholds"><span>Score ≥ {item.min_score.toFixed(0)}</span><span>Profit ≥ {formatCoins(item.min_profit)}</span><span>ROI ≥ {formatPercent(item.min_roi)}</span></div>{item.current_opportunity ? <div className="watchlist-current"><ScorePill score={item.current_opportunity.opportunity_score} classification={item.current_opportunity.classification} /><RiskBadge risk={item.current_opportunity.manipulation_risk} /><span>{formatCoins(item.current_opportunity.net_profit)} / unit</span></div> : <small className="muted-copy">Waiting for a fresh qualified signal.</small>}<button className="text-button watchlist-pause" onClick={() => toggleWatchlist.mutate({ id: item.id, is_active: !item.is_active })}>{item.is_active ? 'Pause alerts' : 'Resume alerts'}</button></>}</div>)}</div> : <div className="table-card empty-state"><h3>Your watchlist is empty.</h3><p>Open a Bazaar item and press Add to watchlist to start receiving local alerts.</p><Link className="secondary-button empty-action-button" href="/bazaar">Open Bazaar</Link></div>}
      </section>

      <section className="tool-section section-header-spaced">
        <div className="section-header"><div><div className="eyebrow">EVENT LOG</div><h2>Recent alerts</h2></div><div className="heading-actions"><span className="muted-label">NO AUTOMATED TRADES</span>{unread > 0 && <button className="text-button" onClick={() => readAll.mutate()}><CheckCheck size={14} /> Mark all read</button>}</div></div>
        {alerts.isLoading ? <div className="table-card tool-loading">Scanning current alert log…</div> : alerts.data?.length ? <div className="table-card alert-list">{alerts.data.map((alert) => <div className={`alert-row ${alert.is_read ? 'alert-row-read' : ''}`} key={alert.id}><div className="alert-icon"><Bell size={15} /></div><div className="alert-copy"><div><strong>{alert.description}</strong><span className="alert-time">{new Date(alert.created_at).toLocaleString()}</span></div><div className="alert-meta"><span>{alert.item_key.split(':')[0]}</span><span>{alert.alert_type.replaceAll('_', ' ')}</span>{alert.risk && <RiskBadge risk={alert.risk} />}</div></div><div className="alert-actions">{alert.estimated_profit != null && <span className="positive number-cell">{formatCoins(alert.estimated_profit)}</span>}{!alert.is_read && <button className="secondary-button compact-button" onClick={() => read.mutate(alert.id)} disabled={read.isPending}>Read</button>}<Link className="icon-button" href={`/bazaar/${encodeURIComponent(alert.item_key.split(':')[0])}`} aria-label="Open item"><ExternalLink size={14} /></Link></div></div>)}</div> : <div className="table-card empty-state"><h3>No alerts yet.</h3><p>Alerts appear when a watched item crosses its score, profit, and ROI thresholds.</p></div>}
      </section>
    </>
  );
}
