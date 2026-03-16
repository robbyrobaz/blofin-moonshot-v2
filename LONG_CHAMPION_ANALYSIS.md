# Long Champion Analysis Summary
**Date:** 2026-03-16
**Model:** 6409feee2207

## TL;DR
**The long champion DOES have trades** - the "0 trades" report was a **logging bug**, not a trading bug.

- **Actual champion performance:** 12 trades (9 open, 3 closed)
- **Closed PnL:** -19.9%, -21.4%, -16.6% (all stop-losses)
- **Win rate:** 0% (0/3 wins)
- **Problem:** Log showed FT stats instead of champion stats

## Root Cause: Misleading Logs

**What the log said:**
```
champion long: 6409feee2207 pnl=0.00% trades=0 pf=0.00
```

**Reality:**
- 12 champion trades (9 open, 3 closed)
- -58% total PnL on closed trades
- 0% win rate

**Why:** `champion.py:280-282` logged **FT stats** (forward-test performance) instead of **champion stats** (actual live performance).

## Fix Applied ✅

**File:** `src/tournament/champion.py`

Updated logging to show:
1. Champion trade count (total, open, closed)
2. Champion PnL and profit factor
3. FT stats for reference

**New log format:**
```
champion long: 6409feee22 champ_trades=12 (9 open, 3 closed) pnl=-58.00% pf=0.00 | FT: 0 trades pf=0.00
```

## Why Entry Rate Is Limited

### 1. Position Limit
- MAX_LONG_POSITIONS = 10 (config.py:95)
- Currently: 9/10 filled
- Room for 1 more entry per cycle

### 2. Entry Threshold (NOT an issue)
- Model threshold: 0.7
- Effective threshold: **0.30** (capped by ENTRY_THRESHOLD_FLOOR)
- Recent entry had score=0.591 (well above 0.30) ✅

### 3. Competition with FT Models
**Critical finding:** FT models bypass position limits!
- Total open long positions: **472**
  - FT models: 463 positions (no limit enforced)
  - Champion: 9 positions (MAX_LONG_POSITIONS=10 enforced)

**Code issue:** `forward_test.py:414-452` doesn't check global position limits, only per-model symbol limits.

## Performance Concerns

### Champion Trades (Model 6409feee2207)
| Status | Count | Avg PnL |
|--------|-------|---------|
| Open | 9 | N/A |
| Closed | 3 | -19.3% |
| **Total** | **12** | **-19.3%** |

**Red flags:**
- 0/3 wins (100% stop-loss rate)
- All 3 closed trades hit -5% SL
- No TP hits yet
- This suggests **no edge** in current market regime

## Recommendations

### Immediate (Next Cycle)
1. ✅ **Fix applied:** Updated champion.py logging
2. ⏳ **Restart service:** `systemctl --user restart moonshot-v2.service`
3. ⏳ **Verify new logs:** `journalctl --user -u moonshot-v2.service -f | grep "champion long"`

### Short-term (Next 7 days)
4. **Monitor win rate:** If next 5-10 trades also hit SL, consider demotion
5. **Check regime blocking:** Verify regime hasn't been "bear" (which blocks long entries)
   ```bash
   journalctl --user -u moonshot-v2.service --since "7 days ago" | grep "regime="
   ```
6. **Investigate FT position leak:** Why do FT models have 463 open positions?

### Medium-term (Next 30 days)
7. **Consider raising MAX_LONG_POSITIONS:** If hunting rare spikes, need more lottery tickets (10 → 15+)
8. **Add FT position limits:** Enforce global limits for FT models too
9. **Demotion criteria:** Define champion demotion threshold (e.g., PF < 0.5 after 20 trades)

## Key Metrics to Watch

After service restart, monitor these in next 4-8 cycles:

| Metric | Current | Target | Red Flag |
|--------|---------|--------|----------|
| Champion trades | 12 | Increasing | Stagnant |
| Open positions | 9 | 8-10 | Stuck at 10 |
| Win rate | 0% | >40% | <20% after 20 trades |
| Avg closed PnL | -19.3% | >0% | Still negative after 10 more |

## Files Modified
- ✅ `src/tournament/champion.py` - Fixed logging
- ✅ `docs/long_champion_debug.md` - Detailed analysis
- ✅ `LONG_CHAMPION_ANALYSIS.md` - This summary

## Verification
```bash
# Restart service
systemctl --user restart moonshot-v2.service

# Watch next cycle (wait up to 4 hours for timer)
journalctl --user -u moonshot-v2.service -f | grep -E "(champion long|ENTRY LONG)"
```

**Expected output:**
```
champion long: 6409feee22 champ_trades=XX (X open, X closed) pnl=X.XX% pf=X.XX | FT: 0 trades pf=0.00
```

## Conclusion

**Problem:** Logging bug made it appear long champion had 0 trades
**Reality:** Long champion has 12 trades but 0% win rate
**Fix:** Updated logging to show champion stats (applied)
**Next:** Monitor performance; consider demotion if losses continue

**STATUS:** Issue diagnosed ✅ | Fix applied ✅ | Verification pending ⏳
