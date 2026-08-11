# Minecraft companion plan

The Fabric companion is deliberately scheduled after the web/backend core. It will be an informational client for `/skyflip`, `/skyflip bazaar`, `/skyflip ah`, `/skyflip item <query>`, and `/skyflip watchlist`, plus a read-only HUD summary.

The mod will never automate gameplay. Specifically out of scope are purchases, auction claiming, Bazaar order placement, selling, menu clicking, macros, packet-level actions, and background gameplay automation. Version-specific Minecraft code will stay isolated in `apps/minecraft-mod` when the project is started.

