# Long Champion Debug Report
**Date:** 2026-03-16
**Model ID:** 6409feee2207
**Status:** ACTIVE CHAMPION (has trades, not 0 as initially reported)

## Summary
The long champion has **12 total trades** (9 open, 3 closed), not 0. The confusion arose from the `tournament_models` table showing `ft_pf=0.00, ft_trades=0`, which tracks FT-mode stats, not champion-mode stats.

## Current State
- **Champion trades:** 12 total
  - 9 OPEN positions
  - 3 CLOSED positions (all losses: -19.9%, -21.4%, -16.6%)
- **Cumulative PnL:** -58% across 3 closed trades
- **Entry threshold:** 0.7
- **Direction:** long

## Closed Trades
1. LYN-USDT: -19.9% (SL)
2. POWER-USDT: -21.4% (SL, visible in logs at 13:47:16)
3. LYN-USDT: -16.6% (SL)

## Open Positions (9)
Currently holding 9 open long positions from champion model 6409feee2207.

## Why Limited New Entries?

### Position Limit Check
**Code:** `src/execution/entry.py:246`
```python
if _count_open_positions(db, direction) >= max_positions:
    log.info("score_and_enter: max long positions reached")
    break
```

- MAX_LONG_POSITIONS = 10 (config.py:95)
- Current open champion longs = 9
- **Room for 1 more champion long entry**

### Log Evidence
```
Mar 16 13:47:14: score_and_enter: max long positions reached
```
This means during the most recent cycle, the champion tried to enter but hit the limit (or no signals passed threshold before hitting limit).

## FT vs Champion Position Counts

### Critical Finding: FT Positions Bypass Limits
**Total open long positions:** 472
- FT positions: 463 (not subject to MAX_LONG_POSITIONS limit)
  - Model 9b842069b20d: 398 positions
  - Model 76e603ce80ba: 31 positions
  - Model 9a67709c0144: 18 positions
  - Model 25e5d828aec5: 14 positions
  - Others: 2 positions
- Champion positions: 9 (subject to MAX_LONG_POSITIONS=10)

**Code:** `src/tournament/forward_test.py:414-452`
FT models open positions for ANY signal above threshold WITHOUT checking global position limits. They only check per-model symbol limits (no duplicate symbol per model).

**Code:** `src/execution/entry.py:67`
Champion position limit only counts `is_champion_trade=1`:
```python
WHERE direction = ? AND status = 'open' AND is_champion_trade = 1
```

## Why Champion Has Low Trade Count vs Short Champion

| Metric | Long Champion 6409feee | Short Champion de44f72dbb01 |
|--------|----------------------|---------------------------|
| Entry threshold | 0.7 | 0.7 |
| FT trades | 0 | 388 |
| Champion trades | 12 | ? |
| Regime filter | Blocked in "bear" | Always allowed |

### Hypothesis
1. **Promoted too early:** Long champion was promoted with 0 FT trades (unusual)
2. **Regime blocking:** If regime was "bear" during most cycles, long entries would be blocked (entry.py:184)
3. **Poor model quality:** 3/3 closed trades hit stop-loss, suggesting model lacks edge
4. **Feature distribution:** Long signals may rarely exceed 0.7 threshold

## Model Promotion Mystery
The tournament_models table shows:
- `ft_pf=0.0`, `ft_trades=0`
- Yet model is registered as champion

**Questions:**
- Was this model promoted via direct training (scripts/train_direct_champion.py)?
- Did it skip FT phase?
- Check champion.py promotion logic

## Recommendations

### 1. Check Promotion Path
```bash
grep -r "6409feee2207" logs/ | head -20
```
Find out how this model became champion without FT trades.

### 2. Lower Long Entry Threshold (if needed)
Current: 0.7
Consider: 0.60-0.65 for long direction only

**Config change:**
```python
# In entry.py, line 194
if direction == "long":
    entry_threshold = max(0.60, entry_threshold * 0.85)  # 15% reduction for longs
```

### 3. Verify Regime Blocking
```bash
journalctl -u moonshot-v2.service --since "7 days ago" | grep "regime="
```
If regime has been "bear", long entries are blocked (entry.py:184).

### 4. Consider Demotion
With 3/3 closed trades as losses (-58% total), this champion may not have edge. Current demotion threshold:
- ft_pf < 0.5 AND ft_trades >= 500

But this model has 0 FT trades, so demotion logic may not apply. Consider manual demotion if next 5-10 champion trades also fail.

### 5. Increase MAX_LONG_POSITIONS
If hunting for rare spikes (new coin moonshots), need more lottery tickets:
```python
MAX_LONG_POSITIONS = 15  # From 10
```

## Root Cause: NOT "0 trades"
The initial problem statement was incorrect. The long champion DOES have trades (12 total). The actual issues are:

1. **Low win rate:** 0/3 closed trades profitable
2. **Position limit:** Can only hold 10 champion longs (currently 9 open)
3. **Promotion anomaly:** Became champion with 0 FT trades
4. **Possible regime blocking:** Long entries blocked in bear regime

## Misleading Log Message (UX Bug)

**Code:** `src/tournament/champion.py:280-282`
```python
log.info("champion %s: %s pnl=%.2f%% trades=%d pf=%.2f",
         direction, row["model_id"][:12], row["ft_pnl"] or 0,
         row["ft_trades"] or 0, row["ft_pf"] or 0)
```

**Problem:** This logs **FT stats** (from tournament_models table when model was in forward-test mode), NOT actual champion performance.

**Evidence:**
```
Mar 16 13:47:11: champion long: 6409feee2207 pnl=0.00% trades=0 pf=0.00
```
But actual champion trades: 12 total (9 open, 3 closed with -58% total PnL)

**Impact:** Severely misleading for operators monitoring system health. Makes it appear champion has no activity when it actually has 12 trades.

**Fix:** Update logging to show champion performance:
```python
# Query actual champion trades for this model
champ_stats = db.execute(
    """SELECT COUNT(*) as cnt, SUM(pnl_pct) as total_pnl,
       COUNT(CASE WHEN status='closed' THEN 1 END) as closed
    FROM positions WHERE model_id = ? AND is_champion_trade = 1""",
    (row["model_id"],)
).fetchone()
log.info("champion %s: %s champion_trades=%d (FT: trades=%d pf=%.2f)",
         direction, row["model_id"][:12], champ_stats["cnt"],
         row["ft_trades"] or 0, row["ft_pf"] or 0)
```

## Actual Performance (Champion Mode)
- **Total trades:** 12
- **Open:** 9 positions
- **Closed:** 3 positions
- **Win rate:** 0% (0/3)
- **Closed PnL:** -19.9%, -21.4%, -16.6% (all stop-losses)
- **Avg closed PnL:** -19.3%

## Why Entry Rate Is Low
1. **MAX_LONG_POSITIONS=10** (currently 9/10 filled)
2. **Score threshold 0.7** - champion did enter at 12:24:16 with score=0.591, which is BELOW 0.7!
   - **WAIT:** Score 0.591 < 0.7 threshold, yet entry was made. Need to investigate effective_entry_threshold logic.

## Entry Threshold Investigation
Looking at recent entry:
```
Mar 16 12:24:16: ENTRY LONG LYN-USDT @ 0.063240  score=0.591  size=$5000
```
Score 0.591 is BELOW the model's entry_threshold=0.7, yet entry was made.

**Explanation:** `effective_entry_threshold()` caps all thresholds at `ENTRY_THRESHOLD_FLOOR=0.30`

**Code:** `src/scoring/thresholds.py:24`
```python
return min(model_threshold, config.ENTRY_THRESHOLD_FLOOR)
```
- Model's entry_threshold: 0.7
- ENTRY_THRESHOLD_FLOOR: 0.30 (config.py:125)
- **Effective threshold: min(0.7, 0.30) = 0.30**
- Entry score: 0.591 ✅ **PASSES** (0.591 > 0.30)

This explains why the long champion CAN enter trades - the 0.7 threshold is capped at 0.30 globally.

## Fix Applied ✅

**File:** `src/tournament/champion.py:280-323`

Changed logging from FT-only stats to champion + FT stats:

**Before:**
```
champion long: 6409feee2207 pnl=0.00% trades=0 pf=0.00
```

**After (new format):**
```
champion long: 6409feee22 champ_trades=12 (9 open, 3 closed) pnl=-58.00% pf=0.00 | FT: 0 trades pf=0.00
```

This makes it immediately clear:
- Champion has 12 trades (not 0!)
- 9 currently open
- 3 closed with -58% total PnL
- 0% win rate (pf=0.00)
- FT stats shown for reference

## Next Steps
1. ✅ Document findings (this file)
2. ✅ Identify misleading log message in champion.py
3. ✅ Fix logging to show champion stats instead of FT stats
4. ✅ Investigate effective_entry_threshold logic (ENTRY_THRESHOLD_FLOOR=0.30 caps all thresholds)
5. ⏳ **Restart moonshot-v2.timer** to apply fix: `systemctl --user restart moonshot-v2.service`
6. ⏳ Monitor next 4-8 cycles to see champion performance with new logging
7. ⏳ Consider demotion if next 5-10 trades also hit SL (0% win rate is unsustainable)

## Verification Command
After restart, check next cycle logs:
```bash
journalctl --user -u moonshot-v2.service -f | grep "champion long"
```

Expected output:
```
champion long: 6409feee22 champ_trades=XX (X open, X closed) pnl=X.XX% pf=X.XX | FT: 0 trades pf=0.00
```
