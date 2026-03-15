# LONG Champion Promotion Fix — 2026-03-15

## Problem Summary

LONG champion promotion was failing due to **champion.py using SHORT backtest gates for BOTH directions**.

### Observed Behavior
- Current LONG FT model: `9b842069b20d` with BT PF=0.79, BT precision=0.282, ci_lower=0.776
- Model passes LONG gates (PF≥0.5, prec≥0.15, ci≥0.4) but was not being promoted
- Historical LONG champion `131bc99f3f65` was promoted on 2026-03-09 but immediately retired for failing gates (BT PF=0.47)
- LONG pipeline was thin: only 1 FT model, 12 backtest models, none passing promotion check

### Root Cause

**File:** `src/tournament/champion.py:94-108`

The `crown_champion_if_ready()` function used hardcoded SHORT gates for both directions:

```python
# BEFORE (incorrect)
candidate = db.execute(
    """SELECT ... WHERE ...
       AND bt_pf >= ?
       AND bt_precision >= ?
       AND bt_ci_lower >= ?
       ...""",
    (direction, MIN_BT_PF, MIN_BT_PRECISION, MIN_BT_TRADES, BOOTSTRAP_PF_LOWER_BOUND),
).fetchone()
```

This meant LONG models were checked against:
- MIN_BT_PF = 1.0 (instead of MIN_BT_PF_LONG = 0.5)
- MIN_BT_PRECISION = 0.20 (instead of MIN_BT_PRECISION_LONG = 0.15)
- BOOTSTRAP_PF_LOWER_BOUND = 0.8 (instead of BOOTSTRAP_PF_LOWER_BOUND_LONG = 0.4)

LONG models can't reach SHORT thresholds in current market conditions (altcoin longs struggling in neutral/bear regime).

## Fix Applied

### 1. Updated `champion.py` imports

Added direction-specific gate configs:
```python
from config import (
    BOOTSTRAP_PF_LOWER_BOUND,
    BOOTSTRAP_PF_LOWER_BOUND_LONG,  # NEW
    MIN_BT_PF,
    MIN_BT_PF_LONG,                  # NEW
    MIN_BT_PRECISION,
    MIN_BT_PRECISION_LONG,           # NEW
    ...
)
```

### 2. Updated `crown_champion_if_ready()` to use direction-specific gates

**File:** `src/tournament/champion.py:92-111`

```python
# Select direction-specific gates
min_bt_pf = MIN_BT_PF_LONG if direction == "long" else MIN_BT_PF
min_bt_precision = MIN_BT_PRECISION_LONG if direction == "long" else MIN_BT_PRECISION
min_bootstrap = BOOTSTRAP_PF_LOWER_BOUND_LONG if direction == "long" else BOOTSTRAP_PF_LOWER_BOUND

# Find best FT candidate using correct gates
candidate = db.execute(
    """SELECT ... WHERE ...
       AND bt_pf >= ?
       AND bt_precision >= ?
       AND bt_ci_lower >= ?
       ...""",
    (direction, min_bt_pf, min_bt_precision, MIN_BT_TRADES, min_bootstrap),
).fetchone()
```

### 3. Improved logging

Updated debug message to show which gates were applied:
```python
log.debug("crown_champion %s: no qualifying candidates (failed BT gates: pf>=%.2f, prec>=%.2f, ci>=%.2f)",
          direction, min_bt_pf, min_bt_precision, min_bootstrap)
```

## Configuration Gates (2026-03-15)

### SHORT (conservative — established market behavior)
- MIN_BT_PF = 1.0
- MIN_BT_PRECISION = 0.20
- BOOTSTRAP_PF_LOWER_BOUND = 0.8

### LONG (relaxed — hunting rare new coin spikes)
- MIN_BT_PF_LONG = 0.5
- MIN_BT_PRECISION_LONG = 0.15
- BOOTSTRAP_PF_LOWER_BOUND_LONG = 0.4

**Rationale:** LONG strategy targets asymmetric payoffs (TP=30%, SL=5%). Precision of 15% at 6:1 reward/risk can be profitable despite many losers. Lower gates allow rare "moonshot" winners to compensate for high loss rate.

## Pipeline Strengthening

### Generated 30 New Challengers (2026-03-15 12:25)
- 15 LONG models
- 15 SHORT models
- Directionally balanced to prevent short-only drift
- Variety of model types: LightGBM, XGBoost, CatBoost
- Confidence thresholds: 0.3, 0.4, 0.5, 0.6, 0.7
- Feature subsets: core, extended, price-heavy, volume-heavy, volatility-heavy

### Backtest Results
**Status:** In progress (started 12:25, ~50 min elapsed)
- Processing: 27 LONG + 26 SHORT models
- Expected completion: ~13:30-14:00 (total runtime 60-90 min for 53 models)
- Results will be auto-processed by tournament pipeline on next cycle

**Note:** Models passing gates will auto-promote to forward_test; failed models will auto-retire. No manual intervention needed.

## Current LONG Pipeline Status

### Forward Test
- **9b842069b20d** — BT PF=0.79, prec=0.282, ci_lower=0.776, FT trades=0
  - ✅ Passes all LONG gates
  - Promoted to FT: 2026-03-15 04:16
  - Will be eligible for champion once ft_trades ≥ 20 and ft_pnl_last_7d > 0

### Backtest
- 12 LONG models currently in backtest stage
- 30 NEW challengers added (15 LONG, 15 SHORT)
- Awaiting backtest results to identify additional promotable models

## Expected Outcome

1. **Immediate:** LONG FT model `9b842069b20d` will be auto-promoted to champion once it accumulates 20+ FT trades (within ~2-3 cycles at current volume)
2. **Short-term:** Some of the 30 new challengers will pass LONG gates (expected 1-3 models at ~5-10% pass rate)
3. **Medium-term:** LONG pipeline will grow to 5-10 FT models, providing better champion candidates

## Verification

### Before Fix
```sql
-- No LONG models passing promotion check (using SHORT gates)
SELECT COUNT(*) FROM tournament_models
WHERE direction='long' AND stage='forward_test'
  AND bt_pf >= 1.0  -- SHORT gate (too high!)
  AND bt_precision >= 0.20;  -- SHORT gate (too high!)
-- Result: 0
```

### After Fix
```sql
-- LONG models now checked against correct gates
SELECT COUNT(*) FROM tournament_models
WHERE direction='long' AND stage='forward_test'
  AND bt_pf >= 0.5  -- LONG gate (correct)
  AND bt_precision >= 0.15;  -- LONG gate (correct)
-- Result: 1 (9b842069b20d)
```

### Live Test (2026-03-15 13:13 UTC)
Executed `crown_champion_if_ready()` manually:
- ✅ Function executed successfully
- ✅ Used SHORT gates (PF≥1.0, prec≥0.20) for SHORT direction
- ✅ Used LONG gates (PF≥0.5, prec≥0.15) for LONG direction
- ✅ Promoted new SHORT champion `e6a96f6aa23d` (BT PF=1.11 passes SHORT gates)
- ✅ Did NOT promote LONG champion (correctly — LONG FT model has 0 trades, needs 20+)
- ✅ Logged applied gates in debug output

**Fix confirmed working in production.**

## Related Files Modified

1. `src/tournament/champion.py` — promotion logic (3 changes)
   - Added direction-specific gate imports
   - Updated `crown_champion_if_ready()` to select gates by direction
   - Enhanced logging to show applied gates

## Future Monitoring

1. Watch LONG champion promotion in next 2-3 cycles (should auto-promote `9b842069b20d`)
2. Monitor LONG backtest pass rate (target: 5-10% of challengers passing gates)
3. Track LONG FT pipeline growth (target: 5-10 active models)
4. Evaluate if LONG gates need further adjustment based on real-world FT performance

## Lessons Learned

1. **Always use direction-specific parameters** — LONG and SHORT have fundamentally different edge profiles in crypto
2. **Test gate logic with both directions** — easy to miss hardcoded values when adding new features
3. **Monitor pipeline health by direction** — thin pipeline (1 FT model) was a red flag
4. **Backtest pass rate should match expected market edge** — LONG is harder (moonshot hunting), so lower pass rate is expected and correct

---

**Status:** Fix applied, backtest running, awaiting results.
**Next Check:** 2026-03-15 evening cycle (20:16 UTC) to verify LONG FT model trades accumulating.
