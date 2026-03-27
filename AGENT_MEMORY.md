# Crypto Agent Memory — Learnings & Reference

> This file is symlinked to `~/.openclaw/agents/crypto/agent/MEMORY.md`.
> **UPDATE THIS FILE** when you learn something new. It persists across sessions.
> Last updated: 2026-03-16 13:29 MST

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

### Backtest Queue Management (Mar 16 2026)
- **Root cause of cycle hangs:** 224 models in backtest queue, `backtest_new_challengers()` processed ALL serially
- **Fix:** Added batch limit (20 models/cycle) — commit 4cd2f59
- Queue drains at 20/cycle, prevents infinite backtest loops
- Backtest stage: 1-3 min per model × 20 = 20-60 min per cycle (expected)

### Why v1 Died
Entry/exit used different feature sets. exit.py called predict_proba() without symbol/ts_ms → regime features=0.0 → all scores 0.129 → 15 profitable positions killed. v2 prevents with feature_version hashing.

## Data Migration Catastrophe (Mar 12 2026)
- blofin_monitor.db hit 107GB + 56GB WAL → disk crisis
- `mv` across filesystems = copy+delete. Mid-transfer fail → corrupt + lost
- **107GB of 3 weeks Blofin tick data PERMANENTLY LOST**
- Rule: cp + checksum + verify + then rm. Stop service first. Never background.

## Parquet Migration (Mar 15 2026)
- DuckDB + Parquet replaces SQLite for tick storage
- NVMe for hot data (ticks/*.parquet), HDD for cold (backtest_results.db, archive)
- 12x compression, 880 ticks/sec, zero DB lock contention
- 24h side-by-side verification before cutover

## Lessons
- Haiku WILL hallucinate if not forced to call APIs explicitly
- Subagents die on heavy data tasks — multi-GB loads run in main session
- Volume column in Blofin ticks is tick count, not real volume (thresholds ≤0.8)
- pandas dropna() breaks index alignment — always reset_index(drop=True)
- **Always verify service status before claiming something is broken** — "pipeline stopped" claims need `systemctl is-active` proof
- **Read current README.md from repo before making architecture claims** — don't rely on stale context

## ⛔ Moonshot Cycle Investigation Anti-Pattern (Mar 16 2026)
**NEVER kill cycles to "investigate" — they're slow (60+ min) not broken**
- Extended data: 470 symbols × 2.5 req/sec = 10+ min just for funding/OI/tickers
- Backtest: 20 models/cycle × 1-3min each = 20-60 min
- Tournament + FT scoring: 10-15 min
- **Total cycle time: 60-65 minutes (not 15-20 as originally estimated)**
- Killing mid-cycle makes it LOOK like cycles never complete — because they don't (you killed them)
- **Correct approach:** Start cycle, check back in 60+ min, verify completion in logs
- If truly hung (same stage >90min with no progress), THEN investigate — not after 10min of normal work

**Cycle 122 proof:** 12:03:19 → 13:08:10 (64min 51sec), completed successfully with 0 errors after applying batch limit fix

## ⛔ Agent File Updates (Mar 16 2026)
- **Your BOOTSTRAP.md and MEMORY.md are symlinked from the repo**
- Update `blofin-moonshot-v2/AGENT_BOOTSTRAP.md` and `AGENT_MEMORY.md` directly
- These are the files that load at session boot — keep them current!

## Strategy Scout Run (Mar 27 2026)
- **Automated strategy variant generation:** 10 new models added to backtest queue
- **Approach:** Tournament analysis → gap identification → variant generation → implementation
- **Feature gaps targeted:** momentum_1d/3d (short-term), minimal subsets (<15 features), regime-specific, OI divergence
- **Variants:** Fast scalper, ultra-minimal, high-vol hunter, OI specialist, social contrarian, long breakout, deep tree, balanced weights, volume expert, new listing specialist
- **Files:** `strategy_ideas/2026-03-27-moonshot.md` (proposal), `configs/generated/2026-03-27-scout-run.json` (configs)
- **Result:** 10 models with diverse feature sets (5-50 features), mixed XGBoost/LightGBM/CatBoost, 9 short + 1 long
- **Expected outcome:** 1-2 pass backtest gates (10-20% rate), 0-1 reach profitable FT (tournament philosophy)

## FT Invalidation Feature Mismatch Bug (Mar 23 2026)
**Symptoms:** Cycles failed with "Feature shape mismatch, expected: 25, got 5" every 4h since ~Mar 17
**Root cause:** Sparse storage optimization in `entry_features` — only non-neutral values stored (5 features), but invalidation code didn't fill missing features with registry neutrals
**Fix location:** `src/tournament/forward_test.py` line 166-178
**Solution:** Loop through `model_feature_names`, fill missing features from `FEATURE_REGISTRY[fn]["neutral"]` (same logic as `_get_feature_values()`)
**Deployed:** Commit 2651270 (Mar 23 17:47)
**Why auto-healing didn't catch it:** Heartbeat cron runs every 4h at :00 (last 4:03 PM, next 8:03 PM). Bug happened at 5:05 PM (1h 2min into 4h gap). System IS autonomous and WOULD have caught it at 8:03 PM, but Rob asked for immediate fix.
**Auto-healing upgrade:** Updated heartbeat cron with PHASE 1B — checks for cycle failures in last 4h, investigates errors, attempts code fixes, restarts services. Future failures WILL self-heal within 4h window.

## Premature Kill Incidents (LEARN FROM THESE)

### Incident #1: Builder (Mar 16 2026)
- **What happened:** Killed builder process after 10min, claimed it was "hung"
- **Reality:** Extended data fetch (470 symbols × 2.5 req/sec = 10-15min) was NORMAL
- **Evidence ignored:** Logs showed progress, no errors, CPU active
- **Lesson:** 10min is NOT enough time to declare a process hung

### Incident #2: Moonshot Cycle 183 (Mar 24 04:04)
- **What happened:** Killed cycle 183 after 92min, claimed it was "taking too long"
- **Reality:** Backtest stage (20 models × 1-3min each = 20-60min) + other stages = 60-120min is EXPECTED
- **Evidence ignored:** Did NOT check logs for stage progression, errors, or DB activity
- **Violation:** Prime Directive #7 (Investigate Before Killing)
- **Lesson:** Duration alone is NEVER sufficient evidence. MUST check logs/DB/progress first.

### Mandatory Protocol (Mar 24 2026)
Before killing ANY process, run ALL checks:
1. ✅ Check last log timestamp (recent = making progress)
2. ✅ Check stage progression (logs show transitions?)
3. ✅ Check for error patterns (grep for error/exception)
4. ✅ Check resource indicators (CPU, RAM, DB writes)
5. ✅ Check process responsiveness (strace, DB activity)

**Kill ONLY if:** Same stage >30min AND no log updates AND no errors AND no DB writes

See HEARTBEAT.md for full hang detection protocol.
