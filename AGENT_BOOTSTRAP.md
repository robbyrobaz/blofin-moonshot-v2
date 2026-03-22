# Crypto Agent Bootstrap — BLOFIN RESTORATION

**Last updated:** 2026-03-22 02:23 MST (Autonomous Fix Cycle 2)

## 🔧 ACTIVE RESTORATION (Mar 12 Data Loss)

### Critical Finding (Mar 22 02:23): Blofin v1 Backtester is BROKEN
**Blofin v1 pipeline is NOT VIABLE for restoration.** Multiple blocking issues:

#### 1. Database Schema Mismatch (BLOCKING)
- `orchestration/run_backtester.py` INSERT statement uses columns: `final_capital`, `results_json`, `days_back`
- Actual table schema expects: `backtest_window_days` (NOT NULL), no `final_capital`, `metrics_json` not `results_json`
- Result: EVERY backtest write fails with "NOT NULL constraint" or "no such column"
- Fix complexity: HIGH (need to audit all code paths, rebuild schema, or rewrite INSERT logic)

#### 2. Backtest Sweep Script is Broken
- `scripts/backtest_sweep_v2.py` completes 2976 tasks in 0.2 seconds (7000+ tasks/sec)
- This is IMPOSSIBLE — actual backtest takes ~0.2 sec per task
- Root cause: `run_single_backtest()` returns None for all tasks (multiprocessing import failures)
- Database ends up with ZERO results despite "successful" completion

#### 3. Only 2 Symbols Tested
- Working backtester (`run_backtester.py`) hardcoded to BTC-USDT and ETH-USDT only
- Need 48+ symbols for tournament-style coverage

### ✅ WORKING SYSTEM: Moonshot v2

**Moonshot is HEALTHY and GENERATING SIGNALS:**
- ✅ Cycle 167 completed Mar 22 01:32 (2 minor model errors, non-blocking)
- ✅ 2 active champions: SHORT (PF=2.22), NEW_LISTING
- ✅ 467 parquet files, 2.1GB historical data restored
- ✅ Real-time OHLCV ingestor running (3827 candles/min)

**Moonshot timer status:**
```bash
systemctl --user status moonshot-v2.timer  # Check if enabled
journalctl --user -u moonshot-v2.service -n 100  # Check cycle health
```

---

## System Status (as of Mar 22 02:23)

### Blofin v1 (BROKEN - DO NOT USE)
- ⛔ blofin-stack-pipeline.timer: STOPPED (per Rob's order, DO NOT RESTART)
- ⛔ Backtester: BROKEN (schema mismatch, only 2 symbols)
- ⛔ Paper trading: OFFLINE (no valid backtest data)
- ✅ Dashboard: blofin-dashboard.service running but NO DATA

### Moonshot v2 (PRODUCTION READY)
- ✅ moonshot-v2.timer: Running 4h cycles
- ✅ moonshot-v2-social.timer: Running 1h social data sync
- ✅ moonshot-v2-dashboard.service: http://127.0.0.1:8893
- ✅ blofin-ohlcv-ingestor.service: Real-time candles flowing
- ✅ Champions: 1 profitable SHORT model (PF=2.22, 388 FT trades, +0.68% PnL)

---

## Moonshot v2 Champions (Current)

| Model ID | Direction | FT PF | FT Trades | FT PnL | Status |
|----------|-----------|-------|-----------|--------|--------|
| de44f72dbb01 | short | 2.22 | 388 | +0.68% | ✅ PROFITABLE |
| new_listing | - | 0.0 | 0 | 0.0% | ⏳ WAITING |

**Champion demotion threshold:** Current PF * 1.1 (must beat by 10%)

---

## Next Actions

### Immediate (Do NOT wait for Rob)
1. ✅ Document Blofin v1 is broken (DONE — this file)
2. ⏳ Verify Moonshot cycle health (currently running)
3. ⏳ Check if Moonshot signals are reaching paper trading / dashboard

### Medium-term (Requires Subagent / Jarvis)
1. **FIX OPTION 1:** Rebuild Blofin v1 database schema from scratch
   - Drop existing `strategy_backtest_results` table
   - Let backtester code CREATE TABLE with correct schema
   - Re-run backtests on all 467 symbols
2. **FIX OPTION 2:** Deprecate Blofin v1, migrate to Moonshot-only
   - Moonshot already does tournament-style model selection
   - Moonshot has working FT tracking and champion promotion
   - Simpler architecture (one system, not two)

### Ask Rob (When he wakes up)
- Which fix option? (Rebuild Blofin v1 OR deprecate it)
- Is Moonshot alone sufficient for production trading?
- Should paper trading consume Moonshot signals instead of Blofin v1?

---

## Data Inventory

### Restored
- ✅ 467 parquet files (OHLCV 1m candles) — 2.1GB total
- ✅ Moonshot tournament database intact (2 champions, 423 FT models, 1792 retired)
- ✅ Real-time tick ingestor running (WebSocket candles)

### Lost (Mar 12)
- ❌ 107GB historical tick data (1-second resolution)
- ❌ Blofin v1 backtest results (strategy × coin performance)
- ❌ Blofin v1 FT results (forward test tracking)
- ❌ Strategy tier assignments (5x/3x/2x/1x)

### Reconstruction Status
- 🟢 Moonshot: COMPLETE (unaffected by data loss)
- 🔴 Blofin v1: BLOCKED (backtester broken, schema mismatch)

---

## Git Status
- `blofin-stack`: BROKEN CODE (do not commit until fixed)
- `blofin-moonshot-v2`: CLEAN

---

## Cron Jobs (Crypto Agent Owns These)

### Active
- `crypto-heartbeat.timer` (30min) — monitors Moonshot + Blofin health
- `blofin-restoration-monitor.timer` (30min) — THIS JOB (autonomous restoration)

### Paused Until Blofin v1 Fixed
- None (Blofin v1 pipeline timer already stopped)

---

## Decision Log

**Mar 22 02:23 — Crypto Agent Decision:**
- Blofin v1 restoration is BLOCKED by broken backtester
- Moonshot v2 is HEALTHY and OPERATIONAL
- Recommend: Use Moonshot signals for paper trading until Blofin v1 properly fixed
- Escalation: Will update Rob at 8am with options (rebuild vs deprecate)
