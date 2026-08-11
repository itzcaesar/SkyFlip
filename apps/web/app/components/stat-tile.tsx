import type { ReactNode } from 'react';

export function StatTile({ label, value, detail, tone = 'neutral', icon }: { label: string; value: string; detail?: string; tone?: 'neutral' | 'green' | 'amber' | 'blue'; icon?: ReactNode }) {
  return (
    <div className={`stat-tile stat-${tone}`}>
      <div className="stat-top"><span>{label}</span>{icon}</div>
      <div className="stat-value">{value}</div>
      {detail && <div className="stat-detail">{detail}</div>}
    </div>
  );
}

