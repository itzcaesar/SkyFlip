'use client';

import Link from 'next/link';
import { Bell, Calculator, ChevronDown, Gavel, LayoutDashboard, Pickaxe, Radio, Search, Settings2, ShieldAlert, WalletCards } from 'lucide-react';
import { usePathname } from 'next/navigation';

const primary = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/bazaar', label: 'Bazaar', icon: WalletCards },
  { href: '/auctions', label: 'Auction House', icon: Gavel },
  { href: '/alerts', label: 'Alerts', icon: Bell },
];

const secondary = [
  { href: '/tools/profit-calculator', label: 'Profit Calculator', icon: Calculator },
  { href: '/tools/valuator', label: 'Item Valuator', icon: Search },
  { href: '/settings', label: 'Settings', icon: Settings2 },
];

function NavItem({ item }: { item: (typeof primary)[number] }) {
  const pathname = usePathname();
  const Icon = item.icon;
  const active = item.href === '/' ? pathname === '/' : pathname.startsWith(item.href);
  return (
    <Link className={`nav-item ${active ? 'nav-item-active' : ''}`} href={item.href}>
      <Icon size={15} />
      <span>{item.label}</span>
      {active && <span className="nav-active-dot" />}
    </Link>
  );
}

export function TerminalShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="app-frame">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark"><Pickaxe size={19} strokeWidth={2.5} /></div>
          <div>
            <div className="brand-name">SkyFlip</div>
            <div className="brand-subtitle">MARKET INTELLIGENCE</div>
          </div>
        </div>

        <div className="terminal-status"><span className="status-pulse" /> OVERWORLD MARKET DESK</div>

        <nav className="nav-group" aria-label="Main navigation">
          <div className="nav-label">World</div>
          {primary.map((item) => <NavItem item={item} key={item.href} />)}
          <div className="nav-label nav-label-spaced">Crafting table</div>
          {secondary.map((item) => <NavItem item={item} key={item.href} />)}
        </nav>

        <div className="sidebar-footnote">
          <ShieldAlert size={14} />
          <span>No auto-trading. Check liquidity, risk, and freshness before acting.</span>
        </div>
      </aside>

      <main className="main-shell">
        <header className="topbar">
          <div className="breadcrumb"><span>SKYFLIP</span><ChevronDown size={13} /><strong>BAZAAR OVERWORLD</strong></div>
          <div className="topbar-actions">
            <div className="market-clock"><Radio size={13} /> OVERWORLD FEED <span className="clock-line" /></div>
            <Link className="icon-button" href="/bazaar" aria-label="Search"><Search size={16} /></Link>
            <Link className="user-chip" href="/settings" aria-label="User settings"><span className="user-avatar">G</span><span>Guest</span></Link>
          </div>
        </header>
        <div className="content-shell">{children}</div>
      </main>
    </div>
  );
}
