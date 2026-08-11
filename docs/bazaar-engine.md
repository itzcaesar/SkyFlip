# Bazaar analytics engine

`apps/api/app/services/bazaar_engine.py` computes both supported strategies from the Hypixel product shape:

- `buy_order_to_sell_order`: entry at the current highest buy-order quote and exit at the current lowest sell-offer quote.
- `instant_buy_to_instant_sell`: entry at the current lowest sell-offer quote and exit at the current highest buy-order quote. It commonly has negative net profit and is retained to make the distinction visible.

The engine calculates spread, fee-adjusted net profit, ROI, suggested volume, visible depth, two-sided transaction volume, competition, fill-time estimate, liquidity, confidence, anomaly risk, capital requirement, and score.

### Known-data boundaries

Volatility and momentum remain `null` until multiple observations can support them. Fill time remains `Unknown` when moving-week volume is absent. A zero-volume book is not treated as a profitable opportunity. Confidence is capped below 95% when fewer than ten historical observations exist, so one live snapshot cannot create false certainty.

### Fee policy

The fee policy is configured with `BAZAAR_BUY_FEE_RATE` and `BAZAAR_SELL_FEE_RATE`. It is not scattered through route or UI code. If Hypixel fee rules change, update the policy and tests together.

