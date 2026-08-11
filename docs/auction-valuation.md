# Auction House valuation plan

Auction House is the next market vertical after Bazaar correctness is established. Its planned pipeline is:

1. Capture active auction records with exact timestamps and deduplication keys.
2. Preserve only raw fields required for reprocessing, including item metadata/NBT.
3. Parse type-specific features into an `ItemFingerprint` (base item, rarity, reforge, stars, recombobulation, enchantments, upgrades, gemstones, attributes, pets, skins, and other value-bearing state).
4. Match genuinely comparable fingerprints rather than relying on lowest BIN.
5. Combine trimmed comparable BINs, recent comparable sales, historical medians, feature-adjusted/component value, liquidity, freshness, and outlier rejection.
6. Produce fair value, confidence range, comparable counts, methodology, anomaly reasons, and risk-adjusted opportunity scores.

No Auction House table or UI state is presented as live until that ingestion path exists. This prevents the UI from implying that an unimplemented valuation is reliable.

