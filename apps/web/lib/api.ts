export type Freshness = {
  status: 'LIVE' | 'DELAYED' | 'STALE' | 'UNAVAILABLE';
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
export function getBazaarDetail(productId: string) { return request<BazaarDetail>(`/bazaar/products/${encodeURIComponent(productId)}`); }
export function getBazaarHistory(productId: string, flipType = 'buy_order_to_sell_order') { return request<BazaarHistory>(`/bazaar/products/${encodeURIComponent(productId)}/history?flip_type=${flipType}`); }
