# Crypto Agent Bootstrap — BLOFIN RESTORATION

**Last updated:** 2026-03-22 06:57 MST

## 🔧 ACTIVE RESTORATION (Mar 20 Database Loss)

### What Happened
- Mar 20 2026: Database lost. All code intact in repo.
- Architecture change: tick data feed → 1-min candle WebSocket (blofin-ohlcv-ingestor.service)
- OHLCV data restored: 467 parquet files, 2.1GB at /mnt/data/blofin_ohlcv/1m/

### Current Status ⏳ IN PROGRESS
**RUNNING:** Full backtest sweep v7_fixed (scripts/backtest_sweep_v7_fixed.py)
- Started: 06:40 MST Mar 22
- Coverage: 62 strategies × 467 symbols = 28,954 backtests
- Writing to: strategy_coin_performance table (NOT strategy_backtest_results)
- Rate: ~5 tasks/sec, ~90 min total, ETA ~8:10 MST
- Saves: Batch of 500, 0 errors per batch
- Cron: Opus 30min check (job 5815c435) monitoring progress + next steps

### After Backtest Completes (cron handles this automatically)
1. Verify results in strategy_coin_performance (expect passing gates: PF ≥ 1.35, trades ≥ 100, MDD < 50%)
2. Start paper trading: `systemctl --user start blofin-stack-paper.service`
3. Verify dashboard populated: http://127.0.0.1:8892
4. Cron self-disables when fully restored
5. **ASK ROB** before restarting pipeline timer

---

## System Status (as of Mar 22 06:57)
- ✅ WebSocket ingestor: blofin-ohlcv-ingestor.service (1-min candles flowing)
- ✅ Historical data: 467 parquet files, 2.1GB
- ⏳ Backtest sweep v7: RUNNING (~11% complete, 3000+ rows written)
- ⛔ Paper trading: STOPPED (waiting for backtest completion)
- ✅ Dashboard: blofin-dashboard.service running (port 8892) — waiting for data
- ✅ Moonshot v2: HEALTHY, unaffected

---

## Moonshot v2 — Tournament Status (Mar 17 snapshot, unchanged)

### Champions (3 active)
- **SHORT Champion:** de44f72dbb01, FT_PF=2.22, FT_PnL=0.68% — HEALTHY ✅
- **LONG Champion:** 9b842069b20d, FT_PF=0.22, FT_PnL=-2.01% — needs investigation
- **New Listing:** new_listing, FT_trades=0 — waiting

### Tournament Numbers
| Stage | Count |
|-------|-------|
| Backtest | 32 models |
| FT | 423 models (393 SHORT, 30 LONG) |
| Retired | 1,792 models |
| Open positions | 884 |

---

## Git Status
- `blofin-stack`: multiple sweep script versions (v2-v7) from restoration attempts
- `blofin-moonshot-v2`: CLEAN
