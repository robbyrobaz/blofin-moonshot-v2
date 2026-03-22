# Crypto Agent Memory — Learnings & Reference

> This file is symlinked to `~/.openclaw/agents/crypto/agent/MEMORY.md`.
> **UPDATE THIS FILE** when you learn something new. It persists across sessions.
> Last updated: 2026-03-22 00:24 MST

## Blofin Architecture (Key Decisions)

### Per-Coin Strategy (Feb 25 2026)
- Do NOT build per-coin ML models. Global models stay trained on all coins.
- Use FT performance to find winning coin+strategy pairs. Enable only those.
- `strategy_coin_performance` — 32 coins × 26 strategies, BT + FT metrics per pair
- `strategy_coin_eligibility` — 1,112 rows, live per-coin performance with blacklist

### Ranking & Promotion
- Ranking: `bt_pnl_pct` (compounded PnL %). Not EEP (dead).
- Promotion: min 100 trades, PF≥1.35, MDD<50%, PnL>0
- FT demotion: PF<0.5 AND trades>500 only — never demote early, FT data is the goal
- Paper trading reality gap: slippage 0.052%/side (2.6x worse), fill rate 67%

## Moonshot v2 Architecture

### Non-negotiables
- Champion = best FT PnL (≥20 trades), NEVER AUC
- One `compute_features()` for train, score, AND exit
- Path-dependent labels: hit +30% BEFORE -10% (long), hit -30% BEFORE +10% (short)
- All 343→471 pairs dynamic — no static coin lists
- Backtest gate (relaxed): PF ≥ 0.5, precision ≥ 0.15, trades ≥ 50
- Bootstrap CI on PF: lower bound ≥ 1.0

### New Listing Auto-Entry (Mar 16 2026 — WORKING)
- `days_since_listing` must be computed each cycle (was NULL for all coins until Mar 16 fix)
- `update_days_since_listing()` in `src/data/discovery.py`
- `model_id='new_listing'` requires entry in `tournament_models` table (FK constraint)
- Coins ≤7 days: 2% position, 2x leverage, trailing stop
- **First successful entry:** CFG-USDT at $0.1890 (Mar 16 10:45 AM)
- Feature deployed Mar 16 07:55 but didn't work until 10:45 fix

### Why v1 Died
Entry/exit used different feature sets. exit.py called predict_proba() without symbol/ts_ms → regime features=0.0 → all scores 0.129 → 15 profitable positions killed. v2 prevents with feature_version hashing.

## Data Migration Lessons

### Catastrophe (Mar 12 2026)
- blofin_monitor.db hit 107GB + 56GB WAL → disk crisis
- `mv` across filesystems = copy+delete. Mid-transfer fail → corrupt + lost
- **107GB of 3 weeks Blofin tick data PERMANENTLY LOST**
- Rule: cp + checksum + verify + then rm. Stop service first. Never background.

### Recovery (Mar 21-22 2026)
- Downloaded 1-min OHLCV candles from 3 sources (Blofin, OKX, Binance.US)
- 2.0GB parquet data (406 files) replaces 107GB tick database
- Backtest engine updated to read parquet via DuckDB (commit e9bd5bc)
- All 71 strategies intact, no code changes needed

### WebSocket Ingestor (Mar 22 2026)
- **DON'T:** Build REST poller with 471 API calls/min
- **DO:** Use WebSocket — subscribe once, server pushes updates
- Blofin API: No bulk candles endpoint, must subscribe per-symbol
- WebSocket batching: max 4KB per message (~50 symbols), send 10 batches
- Service: `blofin-ohlcv-ingestor.service` (enabled, auto-restart)
- Output: `/mnt/data/blofin_ohlcv/1m/*.parquet` (append, skip duplicates)

## Lessons Learned

### General
- Haiku WILL hallucinate if not forced to call APIs explicitly
- Subagents die on heavy data tasks — multi-GB loads run in main session
- Volume column in Blofin ticks is tick count, not real volume (thresholds ≤0.8)
- pandas dropna() breaks index alignment — always reset_index(drop=True)
- **Always verify service status before claiming something is broken** — "pipeline stopped" claims need `systemctl is-active` proof
- **Read current README.md from repo before making architecture claims** — don't rely on stale context

### Research & Build
- ⛔ **Research FIRST, build second** — test endpoints, read docs thoroughly
- ✅ **WebSocket > REST** for continuous real-time data streams
- ⛔ **Don't guess API capabilities** — verify with actual curl tests
- ✅ **Ask Rob for clarification** when documentation is unclear

### Moonshot Cycle Investigation (Mar 16 2026)
- ⛔ **NEVER kill cycles to "investigate"** — they're slow (60+ min) not broken
- Extended data: 470 symbols × 2.5 req/sec = 10+ min just for funding/OI/tickers
- Backtest: 20 models/cycle × 1-3min each = 20-60 min
- Tournament + FT scoring: 10-15 min
- **Total cycle time: 60-65 minutes** (not 15-20 as originally estimated)
- Killing mid-cycle makes it LOOK like cycles never complete — because they don't (you killed them)
- **Correct approach:** Start cycle, check back in 60+ min, verify completion in logs

**Cycle 122 proof:** 12:03:19 → 13:08:10 (64min 51sec), completed successfully with 0 errors after applying batch limit fix

## Agent File Updates (Mar 16 2026)
- **Your BOOTSTRAP.md and MEMORY.md are symlinked from the repo**
- Update `blofin-moonshot-v2/AGENT_BOOTSTRAP.md` and `AGENT_MEMORY.md` directly
- These are the files that load at session boot — keep them current!
- Commit and push after updates so changes persist across sessions
