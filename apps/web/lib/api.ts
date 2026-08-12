export type Freshness = {
  status: 'LIVE' | 'DELAYED' | 'STALE' | 'UNAVAILABLE';
  source?: 'hypixel' | 'demo' | null;
  last_success_at?: string | null;
  age_seconds?: number | null;
  message: string;
};

export type BazaarOpportunity = {
  product_id: string;
  product_name: string;
  flip_type: 'buy_order_to_sell_order' | 'instant_buy_to_instant_sell';
  buy_price: number;
  sell_price: number;
  raw_spread: number;
  spread_percentage: number;
  gross_profit: number;
  estimated_fees: number;
  net_profit: number;
  roi: number;
  buy_volume: number;
  sell_volume: number;
  transaction_volume: number;
  suggested_volume: number;
  active_buy_orders: number;
  active_sell_orders: number;
  orderbook_depth: number;
  estimated_liquidity: number;
  estimated_fill_time_seconds: number | null;
  competition_score: number;
  volatility: number | null;
  short_term_momentum: number | null;
  capital_efficiency: number;
  manipulation_risk_score: number;
  manipulation_risk: string;
  confidence_score: number;
  opportunity_score: number;
  classification: string;
  capital_required: number;
  is_qualified: boolean;
  is_stale: boolean;
  score_breakdown: Record<string, number>;
  signal_explanations: string[];
  observed_at: string;
  source_updated_ms: number;
};

export type BazaarPage = { items: BazaarOpportunity[]; page: number; page_size: number; total: number; freshness: Freshness };
export type BazaarStatus = { freshness: Freshness; active_products: number; qualified_opportunities: number; last_source_updated_ms: number | null };
export type BazaarDetail = { product_id: string; product_name: string; is_active: boolean; opportunities: BazaarOpportunity[]; freshness: Freshness };
export type BazaarHistory = { product_id: string; flip_type: string; points: Array<{ observed_at: string; buy_price: number; sell_price: number; spread: number; volume: number; liquidity: number; opportunity_score: number }>; freshness: Freshness };
export type HealthResponse = { status: string; database: { status: string }; redis: { status: string }; worker: { status: string; detail?: string | null }; bazaar: { status: string; detail?: string | null } };
export type AlertItem = { id: number; market: string; item_key: string; alert_type: string; severity: string; description: string; estimated_profit: number | null; confidence: number | null; risk: string | null; is_read: boolean; created_at: string };
export type WatchlistItem = { id: number; product_id: string; product_name: string; flip_type: 'buy_order_to_sell_order' | 'instant_buy_to_instant_sell'; min_score: number; min_profit: number; min_roi: number; is_active: boolean; created_at: string; current_opportunity: BazaarOpportunity | null };
export type MarketSettings = { sell_fee_rate: number; buy_fee_rate: number; stale_after_seconds: number; max_signal_roi_percent: number; max_price_ratio: number; history_retention_days: number; snapshot_retention_days: number; persisted_overrides: string[] };
export type Valuation = { product_id: string; product_name: string; freshness: Freshness; current_buy_order: number | null; current_sell_order: number | null; instant_buy_price: number | null; instant_sell_price: number | null; observed_low: number | null; observed_high: number | null; observed_median: number | null; price_change_percent: number | null; volatility_percent: number | null; liquidity: number | null; confidence: number | null; risk: string | null; history_points: number };
export type CapitalOptimizeRequest = { available_capital: number; risk: 'conservative' | 'balanced' | 'aggressive'; max_fill_time_seconds?: number; minimum_roi: number; minimum_liquidity: number; maximum_concurrent_flips: number };
export type CapitalOptimizeResponse = { available_capital: number; allocations: Array<{ product_id: string; product_name: string; allocation: number; expected_net_profit: number; opportunity_score: number; estimated_fill_time_seconds: number | null; risk: string }>; reserve: number; projected_net_profit: number; is_estimate: boolean };

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api').replace(/\/$/, '');
export const EVENTS_URL = process.env.NEXT_PUBLIC_WS_URL ?? `${API_URL}/events`;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { ...init, headers: { Accept: 'application/json', ...init?.headers }, cache: 'no-store' });
  if (!response.ok) {
    let message = 'Market data is temporarily unavailable.';
    try { const body = await response.json(); if (typeof body.detail === 'string') message = body.detail; } catch { /* retain safe UI error */ }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export function getBazaarPage(params: URLSearchParams) { return request<BazaarPage>(`/bazaar/products?${params.toString()}`); }
export function getBazaarStatus() { return request<BazaarStatus>('/bazaar/status'); }
export function getHealth() { return request<HealthResponse>('/health'); }
export function refreshBazaar() { return request<Record<string, unknown>>('/bazaar/refresh', { method: 'POST' }); }
export function loadDemoBazaar() { return request<Record<string, unknown>>('/bazaar/demo', { method: 'POST' }); }
export function getBazaarDetail(productId: string) { return request<BazaarDetail>(`/bazaar/products/${encodeURIComponent(productId)}`); }
export function getBazaarHistory(productId: string, flipType = 'buy_order_to_sell_order') { return request<BazaarHistory>(`/bazaar/products/${encodeURIComponent(productId)}/history?flip_type=${flipType}`); }
export function getAlerts(unreadOnly = false) { return request<AlertItem[]>(`/alerts?unread_only=${unreadOnly ? 'true' : 'false'}`); }
export function markAlertRead(alertId: number) { return request<AlertItem>(`/alerts/${alertId}/read`, { method: 'POST' }); }
export function markAllAlertsRead() { return request<{ marked_read: number }>('/alerts/read-all', { method: 'POST' }); }
export function getWatchlist() { return request<WatchlistItem[]>('/watchlist'); }
export function addWatchlist(payload: { product_id: string; flip_type: WatchlistItem['flip_type']; min_score?: number; min_profit?: number; min_roi?: number }) { return request<WatchlistItem>('/watchlist', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); }
export function removeWatchlist(id: number) { return request<{ removed: number }>(`/watchlist/${id}`, { method: 'DELETE' }); }
export function getMarketSettings() { return request<MarketSettings>('/settings'); }
export function updateMarketSettings(payload: Partial<Omit<MarketSettings, 'persisted_overrides'>>) { return request<MarketSettings>('/settings', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); }
export function resetMarketSettings() { return request<MarketSettings>('/settings', { method: 'DELETE' }); }
export function searchItems(query: string) { return request<{ items: Array<{ id: string; name: string; market: string }> }>(`/items/search?q=${encodeURIComponent(query)}`); }
export function getValuation(productId: string) { return request<Valuation>(`/valuator?product_id=${encodeURIComponent(productId)}`); }
export function optimizeCapital(payload: CapitalOptimizeRequest) { return request<CapitalOptimizeResponse>('/bazaar/capital-optimize', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); }
