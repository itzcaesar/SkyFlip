'use client';

import Link from 'next/link';
import { Activity, Bell, Calculator, ChevronDown, LayoutDashboard, Radio, Search, Settings2, ShieldAlert, WalletCards } from 'lucide-react';
import { usePathname } from 'next/navigation';

const primary = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/bazaar', label: 'Bazaar', icon: WalletCards },
  { href: '/alerts', label: 'Alerts', icon: Bell, disabled: true },
];

const secondary = [
  { href: '/tools/profit-calculator', label: 'Profit Calculator', icon: Calculator, disabled: true },
  { href: '/tools/valuator', label: 'Item Valuator', icon: Search, disabled: true },
  { href: '/settings', label: 'Settings', icon: Settings2, disabled: true },
];

function NavItem({ item }: { item: (typeof primary)[number] }) {
  const pathname = usePathname();
  const Icon = item.icon;
  const active = item.href === '/' ? pathname === '/' : pathname.startsWith(item.href);
  if (item.disabled) {
    return (
      <div className="nav-item nav-item-disabled" title="This module is planned for the next vertical slice">
        <Icon size={15} />
        <span>{item.label}</span>
        <span className="nav-soon">Soon</span>
      </div>
    );
  }
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
          <div className="brand-mark"><Activity size={19} strokeWidth={2.5} /></div>
          <div>
            <div className="brand-name">SkyFlip</div>
            <div className="brand-subtitle">MARKET INTELLIGENCE</div>
          </div>
        </div>

        <div className="terminal-status"><span className="status-pulse" /> LIVE MARKET DESK</div>

        <nav className="nav-group" aria-label="Main navigation">
          <div className="nav-label">Workspace</div>
          {primary.map((item) => <NavItem item={item} key={item.href} />)}
          <div className="nav-label nav-label-spaced">Tools</div>
          {secondary.map((item) => <NavItem item={item} key={item.href} />)}
        </nav>

        <div className="sidebar-footnote">
          <ShieldAlert size={14} />
          <span>Signals are estimates. Liquidity and freshness always matter.</span>
        </div>
      </aside>

      <main className="main-shell">
        <header className="topbar">
          <div className="breadcrumb"><span>SKYFLIP</span><ChevronDown size={13} /><strong>MARKET DESK</strong></div>
          <div className="topbar-actions">
            <div className="market-clock"><Radio size={13} /> BAZAAR FEED <span className="clock-line" /></div>
            <button className="icon-button" aria-label="Search"><Search size={16} /></button>
            <button className="user-chip" aria-label="User settings"><span className="user-avatar">G</span><span>Guest</span></button>
          </div>
        </header>
        <div className="content-shell">{children}</div>
      </main>
    </div>
  );
}

