export function FreshnessBadge({ status, message }: { status: string; message?: string }) {
  const normalized = status.toLowerCase();
  return (
    <span className={`freshness freshness-${normalized}`} title={message}>
      <span className="freshness-dot" /> {status}
    </span>
  );
}

export function RiskBadge({ risk }: { risk: string }) {
  return <span className={`risk-badge risk-${risk.toLowerCase()}`}>{risk}</span>;
}

export function ScorePill({ score, classification }: { score: number; classification: string }) {
  return <span className={`score-pill score-${classification.toLowerCase()}`}><strong>{score.toFixed(0)}</strong><small>{classification}</small></span>;
}

