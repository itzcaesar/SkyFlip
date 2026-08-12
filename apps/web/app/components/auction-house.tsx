'use client';

import { useState } from 'react';
import { ArrowUpRight, Clock3, DatabaseZap, RefreshCw, Search, X } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { FreshnessBadge, RiskBadge } from '@/app/components/status-badge';
import { getAuctionListings, getAuctionMarket, getAuctionStatus, type AuctionMarketItem } from '@/lib/api';
import { formatCoins, formatPercent } from '@/lib/format';

export function AuctionHouse() {
  const [search, setSearch] = useState('');
  const [submittedSearch, setSubmittedSearch] = useState('');
  const [sort, setSort] = useState('discount');
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<AuctionMarketItem | null>(null);
  const status = useQuery({ queryKey: ['auctions', 'status'], queryFn: getAuctionStatus, refetchInterval: 60_000 });
  const market = useQuery({
    queryKey: ['auctions', 'market', submittedSearch, sort, page],
    queryFn: () => getAuctionMarket(new URLSearchParams({ search: submittedSearch, sort_by: sort, sort_dir: 'desc', page: String(page), page_size: '50' })),
    refetchInterval: 60_000,
  });
  const listings = useQuery({
    queryKey: ['auctions', 'listings', selected?.item_key],
    queryFn: () => getAuctionListings(new URLSearchParams({ item_key: selected?.item_key ?? '', sort_by: 'price', sort_dir: 'asc', page_size: '50' })),
    enabled: Boolean(selected),
    refetchInterval: 60_000,
  });
  const freshness = status.data?.freshness ?? market.data?.freshness;

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPage(1);
    setSubmittedSearch(search.trim());
  }

  function choose(item: AuctionMarketItem) {
    setSelected(item);
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">AUCTION HOUSE / OVERWORLD</div>
          <h1>BIN comparables</h1>
          <p>Normalized public listings with a transparent, local-first valuation baseline.</p>
        </div>
        <div className="heading-actions">
          <FreshnessBadge status={freshness?.status ?? 'SYNCING'} message={freshness?.message} source={freshness?.source} />
          <span className="market-badge"><DatabaseZap size={13} /> {status.data?.active_listings.toLocaleString() ?? '—'} BIN</span>
          <button className="secondary-button" onClick={() => { void status.refetch(); void market.refetch(); }}><RefreshCw size={14} /> Refresh</button>
        </div>
      </div>

      <div className="alert-banner alert-demo"><DatabaseZap size={16} /><span>{market.data?.methodology ?? 'The Auction House worker is collecting public BIN pages. Valuations become more confident as observations accumulate.'}</span></div>

      <section className="auction-toolbar table-card">
        <form className="filter-search auction-search" onSubmit={submit}>
          <Search size={15} />
          <input aria-label="Search auction house items" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search normalized item names…" />
          <button className="primary-button compact-button" type="submit">Scan</button>
          {submittedSearch && <button className="icon-button" type="button" aria-label="Clear search" onClick={() => { setSearch(''); setSubmittedSearch(''); setPage(1); }}><X size={14} /></button>}
        </form>
        <label className="auction-sort"><span>SORT</span><select value={sort} onChange={(event) => { setSort(event.target.value); setPage(1); }}><option value="discount">Best discount</option><option value="price">Lowest BIN</option><option value="listings">Most listings</option><option value="confidence">Confidence</option></select></label>
      </section>

      <div className="table-meta"><span><strong>{market.data?.total.toLocaleString() ?? '—'}</strong> normalized item variants</span><span className="meta-right"><Clock3 size={12} /> {freshness?.age_seconds != null ? `updated ${freshness.age_seconds}s ago` : 'waiting for first cycle'}</span></div>
      <section className="table-card data-table-card auction-market-table">
        {market.isLoading ? <div className="table-loading">Collecting Auction House comparables…</div> : market.isError ? <div className="empty-state"><h3>Auction House data is not ready.</h3><p>Keep the local API running for the collector to finish its first public page sweep.</p></div> : market.data?.items.length ? <div className="table-scroll"><table><thead><tr><th>ITEM VARIANT</th><th>LISTINGS</th><th>LOW BIN</th><th>FAIR VALUE</th><th>DISCOUNT</th><th>CONFIDENCE</th><th>RISK</th><th /></tr></thead><tbody>{market.data.items.map((item) => <tr key={item.item_key}><td><button className="auction-item-button" onClick={() => choose(item)}><span className="item-icon">◇</span><span><strong>{item.item_name}</strong><small>{item.tier} · {item.category} · {item.history_points} observed points</small></span></button></td><td className="number-cell">{item.listings}</td><td className="number-cell positive">{formatCoins(item.low_bin)}</td><td className="number-cell">{formatCoins(item.fair_value)}</td><td className={`number-cell ${item.best_discount_percent != null && item.best_discount_percent > 0 ? 'positive' : ''}`}>{formatPercent(item.best_discount_percent)}</td><td className="number-cell">{item.confidence.toFixed(0)}%</td><td><RiskBadge risk={item.risk} /></td><td><ArrowUpRight size={14} className="muted-icon" /></td></tr>)}</tbody></table></div> : <div className="empty-state"><h3>No current BIN variants match.</h3><p>Try a broader item name, or wait for the first complete Auction House cycle.</p></div>}
      </section>

      {market.data && market.data.total > market.data.page_size && <div className="pagination-row"><button className="secondary-button compact-button" disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>Previous</button><span>PAGE {page} / {Math.ceil(market.data.total / market.data.page_size)}</span><button className="secondary-button compact-button" disabled={page >= Math.ceil(market.data.total / market.data.page_size)} onClick={() => setPage((value) => value + 1)}>Next</button></div>}

      {selected && <section className="auction-detail tool-section">
        <div className="section-header"><div><div className="eyebrow">COMPARABLE LISTINGS</div><h2>{selected.item_name}</h2><p className="muted-copy">{selected.tier} · {selected.category} · fair value {formatCoins(selected.fair_value)} · {selected.confidence.toFixed(0)}% confidence</p></div><button className="icon-button" onClick={() => setSelected(null)} aria-label="Close comparable listings"><X size={16} /></button></div>
        <div className="table-card data-table-card"><div className="table-scroll"><table><thead><tr><th>PRICE</th><th>DISCOUNT TO FAIR</th><th>END TIME</th><th>RISK</th><th>SEEN</th></tr></thead><tbody>{listings.isLoading ? <tr><td colSpan={5}>Loading current comparable listings…</td></tr> : listings.data?.items.map((listing) => <tr key={listing.auction_uuid}><td className="number-cell positive">{formatCoins(listing.price)}</td><td className="number-cell">{formatPercent(listing.discount_percent)}</td><td className="number-cell">{listing.end_at ? new Date(listing.end_at).toLocaleTimeString() : '—'}</td><td>{listing.risk && <RiskBadge risk={listing.risk} />}</td><td className="number-cell">{new Date(listing.last_seen_at).toLocaleTimeString()}</td></tr>)}</tbody></table></div></div>
      </section>}
    </>
  );
}
