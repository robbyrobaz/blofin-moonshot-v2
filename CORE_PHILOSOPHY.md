# CORE PHILOSOPHY — Moonshot v2

## Forward Testing is FREE

**Paper trading costs NOTHING.** Losers don't hurt us. Bad models don't drain capital. FT is pure data collection.

## We Expect 95% Losers

Out of 100 models in FT:
- **95 will lose money** — this is expected and fine
- **5 might break even** — meh
- **0.5-1 will be profitable** — THIS IS THE GOAL

**Never optimize for aggregate metrics.** System-wide win rate, average PF, total PnL across all models — all meaningless.

## The Mission: Find the Top 5 Winners

We're running a tournament to find the **rare models that actually work.** Not to make all models work.

- Generate 100+ challengers per day
- Let them compete in FT (20-200 trades)
- Track ONLY the top performers by `ft_pnl`
- Retire the bottom 95% without guilt

## What This Means Operationally

✅ **DO:**
- Run massive FT — 200+ models is fine, 500 is fine
- Promote aggressively (low BT gates, let models into FT easily)
- Retire ruthlessly (demote only catastrophic losers after 150+ trades)
- Focus on champion performance, not population stats

❌ **DON'T:**
- Try to fix failing models
- Lower gates to "help" models pass
- Worry about invalidation rate or FT backlog size
- Report aggregate win rate or system PnL

## For Moonshot Specifically

**Goal:** Find big movers (±30%) across 343 coins, with bias toward new listings.

**Current drift:** Shorts working better than longs (crypto mean reversion).

**Before pivoting to new coin longs:** VALIDATE if predicting new coin spikes is even viable. Run analysis first, then adjust.

---

*Updated 2026-03-15 by Rob's directive: "Nobody cares if the majority are losers!! That's the point!! Find the few winners!!!"*
