# Bazaar analytics engine

`apps/api/app/services/bazaar_engine.py` computes both supported strategies from the Hypixel product shape:

- `buy_order_to_sell_order`: entry at the current highest buy-order quote and exit at the current lowest sell-offer quote.
- `instant_buy_to_instant_sell`: entry at the current lowest sell-offer quote and exit at the current highest buy-order quote. It commonly has negative net profit and is retained to make the distinction visible.

The engine calculates spread, fee-adjusted net profit, ROI, suggested volume, visible depth, two-sided transaction volume, competition, fill-time estimate, liquidity, confidence, anomaly risk, capital requirement, and score.

### Known-data boundaries

Volatility and momentum are derived from the most recent retained sell-price observations when history exists. Fill time remains `Unknown` when moving-week volume is absent. A zero-volume book is not treated as a profitable opportunity. Confidence ramps conservatively across live cycles and does not reach the highest band until the item has a meaningful observation history. Once enough cycles exist, robust median/MAD checks flag large one-cycle quote deviations; absolute ROI and quote-ratio limits remain as a second safety gate. Signals also require configurable minimum ROI, net profit, liquidity, and confidence.

### Fee policy

The fee policy is configured with `BAZAAR_BUY_FEE_RATE`, `BAZAAR_SELL_FEE_RATE`, and `BAZAAR_FEE_BUFFER_RATE`. The buffer is a conservative execution allowance for quote movement/relisting and is not presented as a platform tax. The policy is not scattered through route or UI code. If Hypixel fee rules change, update the policy and tests together.
