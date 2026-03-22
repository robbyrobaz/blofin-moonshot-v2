# Crypto Agent Bootstrap — BLOFIN RESTORATION

**Last updated:** 2026-03-22 04:05 MST (Heartbeat — Hung Cycle Killed)

## 🔧 ACTIVE RESTORATION (Mar 12 Data Loss)

### Strategy
**PIVOT:** Full backtest sweep has infinite loop bug (hangs at task 2000/2976 on vol_compression_fade_v2). Instead of debugging 62 broken strategies, **restore the 57 profitable pairs that EXISTED before**.

### Current Status
1. ✅ **Tier data SURVIVED** — 57 strategy/coin pairs with tier>0 still in `strategy_coin_performance`
   - Tier assignments intact, but backtest metrics (PF, trades, etc.) are NULL
   - These were the profitable pairs BEFORE the crash
   
2. ⏳ **Backtest sweep ABANDONED** (infinite loop on certain strategies)
   - Issue: Some strategies (vol_compression_fade_v2, possibly others) cause infinite loops
   - Tried: 365→90 days, 5m→15m timeframe, timeouts — still hangs at task 2000
   - Decision: Skip full sweep, just backtest the 57 known-good pairs

### Next Actions
3. Extract list of 57 profitable strategy/symbol pairs from database
4. Run targeted backtests ONLY on those 57 pairs (30 days, 15m timeframe)
5. Populate metrics in strategy_coin_performance
6. Start paper trading
7. Monitor for 24h, then enable pipeline timer (with Rob's approval)

---

## System Status (as of Mar 22 03:22)
- ✅ WebSocket ingestor: blofin-ohlcv-ingestor.service (candles flowing)
- ✅ Historical data: 467 parquet files, 2.1GB (way more symbols than expected 48)
- ⛔ Backtest sweep: KILLED (infinite loop bug)
- ⛔ Paper trading: STOPPED (waiting for backtest metrics)
- ✅ Dashboard: blofin-dashboard.service running (port 8892) — no data yet
- ✅ Moonshot v2: HEALTHY, unaffected

---

## Moonshot v2 — Tournament Status (Mar 22 04:05)

### ⚠️ CRITICAL INCIDENT — 6-Day Hung Cycle
- **Cycle 126** started Mar 16 16:20, hung at `fetch_all_extended` step
- **CPU time:** 325+ hours (infinite loop or deadlock)
- **Action taken:** Killed PID 1968765, restarted service
- **New cycle:** PID 2089996 started Mar 22 04:05

### Champions (2 active)
- **SHORT Champion:** de44f72dbb01, FT_PF=2.22, FT_trades=388, FT_PnL=0.68% — HEALTHY ✅
- **New Listing:** new_listing, FT_trades=0 — waiting

### Tournament Numbers
| Stage | Count |
|-------|-------|
| Backtest | 4 models |
| Champion | 2 models |
| FT | 631 models |
| Retired | 2,280 models |
| Open positions | 890 |
| Candles in DB | 472 symbols |

---

## Git Status
- `blofin-stack`: 2 uncommitted changes
  - orchestration/run_backtester.py (loader fix)
  - scripts/backtest_sweep_v2.py (timeout attempts, 15m timeframe)
- `blofin-moonshot-v2`: CLEAN

---

## Historical Context (Pre-Mar 12)

Blofin v1 was running:
- 72 strategies across 50+ coins
- Dynamic tier system (5x/3x/2x/1x leverage based on FT PF)
- Hourly backtest refresh (blofin-stack-pipeline.timer — STOPPED per Rob's order)
- Paper trading engine tracking performance

**Mar 12 data loss:** 107GB tick data lost, backtests/FT results cleared.
**Restoration status:** OHLCV restored, tier data survived, working on metrics restoration for 57 profitable pairs.
