# Opportunity scoring

The scoring policy lives in `apps/api/app/services/scoring.py` and returns both a 0–100 score and a breakdown.

Positive components total 100:

| Component | Weight | Meaning |
| --- | ---: | --- |
| Profitability | 25 | Net profit relative to a 10% per-unit target |
| ROI | 20 | Net ROI relative to a 15% target |
| Liquidity | 15 | Depth and two-sided visible volume |
| Fill probability | 15 | Transaction volume relative to suggested size |
| Confidence | 15 | Completeness and historical support |
| Stability | 10 | Historical volatility when available; unknown stability is not rewarded fully |

Penalties are explicit: competition up to 5, observed volatility up to 5, manipulation/anomaly risk up to 10, and capital lockup up to 5. The result is clamped to 0–100 and classified as Excellent (90–100), Strong (80–89), Good (70–79), Moderate (60–69), or Weak (<60).

The score is a ranking aid, not a guarantee. The API exposes the breakdown and signal explanations so users can inspect why a row ranked where it did.

