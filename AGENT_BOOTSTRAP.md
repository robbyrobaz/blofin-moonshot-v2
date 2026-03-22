# Crypto Agent Bootstrap

**Last updated:** 2026-03-22 16:03 MST

## ✅ BLOFIN V1 — RESTORED (Mar 22, 2026)

### Restoration Summary (Mar 20-22)
- Mar 20: Database lost. Architecture changed: tick data → 1-min OHLCV candles via WebSocket.
- Mar 21-22: 3 parallel backfill jobs restored 467 parquet files, 2.1GB at /mnt/data/blofin_ohlcv/1m/
- Mar 22: Backtest sweep v7_fixed completed — 20,901 backtests across 45 strategies × 467 symbols
- **1,252 strategy/coin pairs passing gates** (PF ≥ 1.35, trades ≥ 100, MDD < 50%)
- Paper trading: ACTIVE
- Dashboard: LIVE at http://127.0.0.1:8892

## System Status (as of Mar 22 16:03)
- ✅ WebSocket ingestor: blofin-ohlcv-ingestor.service (1-min candles flowing)
- ✅ Historical data: 467 parquet files, 2.1GB (Binance+OKX complete, Blofin partial)
- ✅ Backtest sweep: COMPLETE — 20,901 results, 1,252 passing gates
- ✅ Paper trading: blofin-stack-paper.service ACTIVE
- ✅ Dashboard: blofin-dashboard.service running (port 8892)
- ⛔ Pipeline timer: STOPPED per Rob's order — do NOT restart without approval
- ✅ Moonshot v2: HEALTHY, unaffected

---

## Moonshot v2 — Tournament Status (Mar 22 16:03)

### Champions (2 active)
- **de44f72dbb01:** FT_PnL=0.68%, 388 trades — HEALTHY ✅
- **new_listing:** FT_PnL=0.0%, 0 trades — waiting

### Tournament Numbers
| Stage | Count |
|-------|-------|
| FT | 0 models |
| Champion | 2 models |
| Retired | ~2,941 models |
| Open positions | 858 |

### Notes
- Moonshot cycle running 69 min (started 14:54, normal for extended data)
- 1-min candle coverage: 472 symbols in DB

---

## Git Status
- `blofin-stack`: multiple sweep script versions (v2-v7) from restoration attempts
- `blofin-moonshot-v2`: CLEAN
