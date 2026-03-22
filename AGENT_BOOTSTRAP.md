# Crypto Agent Bootstrap

> This file is symlinked to `~/.openclaw/agents/crypto/agent/BOOTSTRAP.md`.
> **UPDATE THIS FILE** (not the symlink) when state changes. It auto-loads every session.
> Last updated: 2026-03-22 00:24 MST (WebSocket ingestor deployed)

## Session Summary (Mar 22 2026)

**Blofin v1 Data Migration — COMPLETE ✅**
- ✅ OHLCV 1-min data downloaded (2.0GB, 406 parquet files)
- ✅ Backtest engine updated to read parquet via DuckDB
- ✅ WebSocket ingestor LIVE — 182 candles written in first 2 min
- ⏳ Backtest sweep running (768 tasks, ~10 min remaining)
- 📊 Dashboard will populate when backtests complete

**Active Services (Mar 22 00:24):**
- 🟢 `blofin-ohlcv-ingestor.service` — WebSocket candle ingestor (ACTIVE, auto-start enabled)
- 🟢 `blofin-dashboard.service` — Dashboard at port 8892 (ACTIVE)
- 🟢 `moonshot-v2-dashboard.service` — Dashboard at port 8893 (ACTIVE)
- 🔴 `blofin-stack-paper.service` — Paper trading engine (STOPPED, will restart after backtests)
- ❌ `blofin-stack-ingestor.service` — Old tick ingestor (RETIRED, disabled)

**Data Pipeline:**
- Candles: WebSocket → `/mnt/data/blofin_ohlcv/1m/*.parquet` (real-time) ✅
- Backtests: Read parquet via DuckDB → `strategy_backtest_results` table
- Paper trades: Executes top performers → `paper_trades` table (not running yet)

## Moonshot v2 — Tournament Status

### Champions (3 active, separate long/short + new_listing)
- **SHORT Champion:** de44f72dbb01 (XGBoost), BT_PF=0.98, BT_precision=0.246, FT_trades=388, FT_PF=2.22, FT_PnL=0.68%
  - Promoted: 2026-03-16 18:51 (Cycle 127) — **HEALTHY ✅** (best FT performer)
  - Status: Excellent performance, no action needed
- **LONG Champion:** 9b842069b20d (CatBoost), BT_PF=0.79, BT_precision=0.282, FT_trades=39, FT_PF=0.22, FT_PnL=-2.01%
  - Promoted: (timestamp unknown)
  - Status: **BROKEN** — FT PF 0.22 vs BT 0.79 = likely feature drift or regime bug
  - **FIX DISPATCHED:** Builder c_359ae9805aaf1_19cf995ff2c investigating (19:15)
- **New Listing:** new_listing (rule-based), BT_PF=7.53, FT_trades=0 — waiting for next ≤7 day coin

### Services (All ACTIVE as of 14:15)
- `moonshot-v2.timer` — 4h cycle (cycle 123 running, started 13:54)
- `moonshot-v2-social.timer` — 1h social signals (active)
- `moonshot-v2-dashboard.service` — HTTP 200 on port 8893
- Dashboard: http://127.0.0.1:8893/

## Blofin v1 Stack

### Status — DATA RESTORED (00:24 Mar 22)
- **Data pipeline:** WebSocket candle ingestor ACTIVE ✅ (470 symbols, real-time)
- **Backtest sweep:** RUNNING (768 tasks, ~10 min remaining)
- Services: `blofin-ohlcv-ingestor` ACTIVE, `blofin-dashboard` ACTIVE
- Paper trading: STOPPED (will restart after backtests complete)
- Dashboard: http://127.0.0.1:8892 (empty, waiting for backtest results)
- **New candles:** Flowing in real-time to `/mnt/data/blofin_ohlcv/1m/*.parquet`

### WebSocket Ingestor (NEW — Mar 22 00:21)
- **Service:** `blofin-ohlcv-ingestor.service`
- **Tech:** WebSocket (wss://openapi.blofin.com/ws/public)
- **Subscriptions:** 470 symbols × candle1m channel (10 batches of ~50)
- **Output:** `/mnt/data/blofin_ohlcv/1m/{SYMBOL}.parquet` (append, skip duplicates)
- **Performance:** 182 candles written in first 2 min (Mar 22 00:21-00:23)
- **Auto-restart:** enabled, ping every 25s, reconnect on disconnect

### Ranking & Promotion
- Ranking: `bt_pnl_pct` (compounded PnL %)
- Promotion: min 100 trades, PF≥1.35, MDD<50%, PnL>0
- FT demotion: PF<0.5 AND trades>500 only — never demote early

### Architecture
- Do NOT build per-coin ML models — use global models + per-coin eligibility
- Dashboard: NEVER show aggregate PF/WR/PnL — always top performers only

## Autonomous Crons
- **Crypto Heartbeat** — every 4h, health + pipeline scan + card dispatch
- **Auto Card Generator** — every 4h, reads pipeline state, creates cards
- **Profit Hunter** — every 12h, scouts top performers across all pipelines
- **Blofin Daily Backtest** — 2am, refreshes backtest results
- **Blofin Top Performer Alert** — 8am, flags FT PF>2.5 candidates
- **Blofin Weekly FT Review** — Sun 6am, promotes/demotes strategies
- **Backfill Watchdog** — every 10min, monitors historical data backfill

## Critical Rules
- ⛔ Never restart blofin-stack-pipeline.timer without Rob's approval
- ⛔ Never aggregate performance — filter to top performers first
- ⛔ Moonshot: champion = best FT PnL (≥20 trades), NEVER AUC
- ⛔ 95% retirement rate is GOOD (tournament philosophy)
- ⛔ Data migration: COPY-VERIFY-DELETE only (107GB loss Mar 12)
- ⛔ INVESTIGATE BEFORE KILLING — slow ≠ broken (cycles take 60+ min)
