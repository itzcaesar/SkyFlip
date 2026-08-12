'use client';

import { RotateCcw, Save, Settings2 } from 'lucide-react';
import { useState } from 'react';
import { getMarketSettings, resetMarketSettings, updateMarketSettings, type MarketSettings } from '@/lib/api';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

type FormState = Omit<MarketSettings, 'persisted_overrides'>;

export function SettingsPage() {
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ['settings'], queryFn: getMarketSettings });
  const [form, setForm] = useState<FormState | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const formValues = form ?? (query.data ? withoutOverrides(query.data) : null);
  const save = useMutation({ mutationFn: (values: FormState) => updateMarketSettings(values), onSuccess: (data) => { queryClient.setQueryData(['settings'], data); setForm(null); setMessage('Local settings saved. New Bazaar cycles use these thresholds.'); } });
  const reset = useMutation({ mutationFn: resetMarketSettings, onSuccess: (data) => { queryClient.setQueryData(['settings'], data); setMessage('Defaults restored.'); } });
  const update = (key: keyof FormState, value: string) => setForm((current) => ({ ...(current ?? formValues ?? emptyForm()), [key]: Number(value) }));

  return (
    <>
      <div className="page-heading"><div><div className="eyebrow">CRAFTING TABLE / CONFIG</div><h1>Settings</h1><p>Adjust local market policy without touching secrets or infrastructure configuration.</p></div><div className="heading-actions"><span className="market-badge"><Settings2 size={14} /> LOCAL PROFILE</span></div></div>
      {query.isError && <div className="alert-banner alert-error">{query.error instanceof Error ? query.error.message : 'Settings could not be loaded.'}</div>}
      {save.isError && <div className="alert-banner alert-error">{save.error instanceof Error ? save.error.message : 'Settings could not be saved.'}</div>}
      {message && <div className="alert-banner alert-success">{message}</div>}
      {formValues && <form className="table-card settings-form" onSubmit={(event) => { event.preventDefault(); setMessage(null); save.mutate(formValues); }}><div className="section-header"><div><div className="eyebrow">MARKET POLICY</div><h2>Signal controls</h2></div><span className="muted-label">{query.data?.persisted_overrides.length ?? 0} OVERRIDES</span></div><div className="settings-grid"><SettingField label="Sell fee rate" value={formValues.sell_fee_rate} suffix="decimal" step="0.0001" onChange={(value) => update('sell_fee_rate', value)} /><SettingField label="Buy fee rate" value={formValues.buy_fee_rate} suffix="decimal" step="0.0001" onChange={(value) => update('buy_fee_rate', value)} /><SettingField label="Execution buffer" value={formValues.fee_buffer_rate} suffix="decimal" step="0.0001" onChange={(value) => update('fee_buffer_rate', value)} /><SettingField label="Stale after" value={formValues.stale_after_seconds} suffix="seconds" onChange={(value) => update('stale_after_seconds', value)} /><SettingField label="Minimum ROI" value={formValues.min_signal_roi_percent} suffix="percent" step="0.1" onChange={(value) => update('min_signal_roi_percent', value)} /><SettingField label="Minimum net profit" value={formValues.min_signal_net_profit} suffix="coins" step="1" onChange={(value) => update('min_signal_net_profit', value)} /><SettingField label="Minimum liquidity" value={formValues.min_signal_liquidity} suffix="/100" step="1" onChange={(value) => update('min_signal_liquidity', value)} /><SettingField label="Minimum confidence" value={formValues.min_signal_confidence} suffix="percent" step="1" onChange={(value) => update('min_signal_confidence', value)} /><SettingField label="Max signal ROI" value={formValues.max_signal_roi_percent} suffix="percent" onChange={(value) => update('max_signal_roi_percent', value)} /><SettingField label="Max quote ratio" value={formValues.max_price_ratio} suffix="x" step="0.1" onChange={(value) => update('max_price_ratio', value)} /><SettingField label="Anomaly samples" value={formValues.history_anomaly_min_samples} suffix="cycles" onChange={(value) => update('history_anomaly_min_samples', value)} /><SettingField label="Anomaly z-score" value={formValues.history_anomaly_zscore} suffix="robust z" step="0.1" onChange={(value) => update('history_anomaly_zscore', value)} /><SettingField label="Max history deviation" value={formValues.history_max_deviation_percent} suffix="percent" onChange={(value) => update('history_max_deviation_percent', value)} /><SettingField label="Raw history retention" value={formValues.history_retention_days} suffix="days" onChange={(value) => update('history_retention_days', value)} /><SettingField label="Chart retention" value={formValues.chart_retention_days} suffix="days" onChange={(value) => update('chart_retention_days', value)} /><SettingField label="Snapshot retention" value={formValues.snapshot_retention_days} suffix="days" onChange={(value) => update('snapshot_retention_days', value)} /></div><div className="form-actions"><button className="primary-button" type="submit" disabled={save.isPending}><Save size={14} /> {save.isPending ? 'Saving' : 'Save settings'}</button><button className="secondary-button" type="button" onClick={() => { setForm(null); setMessage(null); reset.mutate(); }} disabled={reset.isPending}><RotateCcw size={14} /> Reset defaults</button></div><small className="muted-copy">Fee rates are decimals: 0.0125 means 1.25%. The execution buffer covers quote movement between observation and fill. History checks compare a quote with recent live cycles after the configured sample count. Settings apply to the next collection cycle.</small></form>}
    </>
  );
}

function withoutOverrides(settings: MarketSettings): FormState {
  return {
    sell_fee_rate: settings.sell_fee_rate,
    buy_fee_rate: settings.buy_fee_rate,
    fee_buffer_rate: settings.fee_buffer_rate,
    stale_after_seconds: settings.stale_after_seconds,
    max_signal_roi_percent: settings.max_signal_roi_percent,
    max_price_ratio: settings.max_price_ratio,
    min_signal_roi_percent: settings.min_signal_roi_percent,
    min_signal_net_profit: settings.min_signal_net_profit,
    min_signal_liquidity: settings.min_signal_liquidity,
    min_signal_confidence: settings.min_signal_confidence,
    history_anomaly_min_samples: settings.history_anomaly_min_samples,
    history_anomaly_zscore: settings.history_anomaly_zscore,
    history_max_deviation_percent: settings.history_max_deviation_percent,
    history_retention_days: settings.history_retention_days,
    chart_retention_days: settings.chart_retention_days,
    snapshot_retention_days: settings.snapshot_retention_days,
  };
}

function emptyForm(): FormState {
  return { sell_fee_rate: 0.0125, buy_fee_rate: 0, fee_buffer_rate: 0.0025, stale_after_seconds: 120, max_signal_roi_percent: 500, max_price_ratio: 5, min_signal_roi_percent: 1, min_signal_net_profit: 0, min_signal_liquidity: 20, min_signal_confidence: 55, history_anomaly_min_samples: 12, history_anomaly_zscore: 6, history_max_deviation_percent: 50, history_retention_days: 7, chart_retention_days: 90, snapshot_retention_days: 30 };
}

function SettingField({ label, value, suffix, step = '1', onChange }: { label: string; value: number; suffix: string; step?: string; onChange: (value: string) => void }) {
  return <label className="form-field"><span>{label}</span><div className="input-with-unit"><input type="number" value={value} onChange={(event) => onChange(event.target.value)} step={step} min="0" required /><em>{suffix}</em></div></label>;
}
