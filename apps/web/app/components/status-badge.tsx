export function FreshnessBadge({ status, message, source }: { status: string; message?: string; source?: string | null }) {
  const normalized = status.toLowerCase();
  const isDemo = source === 'demo';
  return (
    <span className={`freshness freshness-${isDemo ? 'demo' : normalized}`} title={isDemo ? `${message ?? ''} Demo data only; not live market prices.` : message}>
      <span className="freshness-dot" /> {isDemo ? 'DEMO DATA' : status}
    </span>
  );
}

export function RiskBadge({ risk }: { risk: string }) {
  return <span className={`risk-badge risk-${risk.toLowerCase()}`}>{risk}</span>;
}

export function ScorePill({ score, classification }: { score: number; classification: string }) {
  return <span className={`score-pill score-${classification.toLowerCase()}`}><strong>{score.toFixed(0)}</strong><small>{classification}</small></span>;
}
