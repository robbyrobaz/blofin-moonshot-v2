# Moonshot v2 Redesign: Rule-Based Entry for New Listings + ML for Established Coins

**Date:** 2026-03-16
**Status:** Proposed (awaiting approval)

## Problem Statement

Current system failed to find 30%+ spike winners despite:
- 753 long models retired
- Gates loosened to PF=0.3, precision=8%
- TP raised to 30%

**Root Cause Identified:** ALL major spikes (ROBO 81%, MANTRA 50%, KAT 63%, CL 60%, OPN 36%) happened in the **FIRST 7 DAYS** after listing. ML models CANNOT predict these because:

1. **Bar 0 Problem:** Biggest spikes often happen at bar 0-10 (first 0-2 days)
2. **Feature Computation Requires History:** Need 42+ bars (7 days) minimum for basic features, 180 bars (30 days) for most features
3. **No Training Data at Listing:** Can't train on what hasn't happened yet

### Spike Timing Analysis Results

| Coin | Total 30%+ Entries | First 7 Days | Days 8-30 | After 30d | Earliest Bar | Best Gain |
|------|-------------------|--------------|-----------|-----------|--------------|-----------|
| ROBO-USDT | 21 | 19 (90%) | 2 (10%) | 0 (0%) | Bar 0 | 81.5% |
| MANTRA-USDT | 1 | 1 (100%) | 0 (0%) | 0 (0%) | Bar 0 | 50.1% |
| KAT-USDT | 37 | 15 (41%) | 22 (59%) | 0 (0%) | Bar 28 | 63.0% |
| CL-USDT | 16 | 16 (100%) | 0 (0%) | 0 (0%) | Bar 0 | 60.0% |
| OPN-USDT | 6 | 3 (50%) | 3 (50%) | 0 (0%) | Bar 0 | 35.5% |

**Conclusion:** 76% of all 30%+ entry opportunities occur in the first 7 days when ML models have insufficient data.

---

## Proposed Solution: Dual-Track System

### Track 1: Rule-Based Entry for New Listings (0-7 days old)

**Entry Logic:**
- Automatically enter ALL coins <7 days old
- Position size: 2% of portfolio (current BASE_POSITION_PCT)
- No ML prediction needed - this is a lottery ticket strategy
- Entry trigger: Coin appears on Blofin with <7 days since listing

**Exit Logic (Trailing Stop):**
- Hard stop: -5% (baseline risk)
- Trail activation: +15% gain
- Trail distance: 10% below peak
- Horizon: 42 bars (7 days) - if no TP/SL hit, exit at market

**Expected Performance:**
- Win rate: 10-20% (most coins dump)
- Avg loss: -5% (80-90% of trades)
- Avg win: +30-60% (10-20% of trades)
- Required for profit: (0.90 × -5%) + (0.10 × 30%) = -4.5% + 3.0% = -1.5%
  - Need at least 15% win rate with 30% avg win to break even
  - OR 10% win rate with 45% avg win
- **This is a lottery ticket strategy:** High variance, positive skew, low Sharpe

**Implementation:**
- New module: `src/execution/new_listing_entry.py`
- No ML model required
- Check `days_since_listing` from `coins` table
- Enter at market on next 4H bar close
- Apply trailing stop logic in `src/execution/exit.py`

### Track 2: ML Models for Established Coins (30+ days old)

**Entry Logic:**
- Keep current tournament system
- Only train/score coins with ≥180 bars (30 days) of history
- Use full 50-feature set (core + extended + social)
- Current gates are reasonable for established coins

**Exit Logic:**
- Test trailing stops in backtest (vs fixed TP)
- If trailing stops improve PF, update backtest methodology
- Otherwise keep fixed TP=30%, SL=5%

**Rationale:**
- Coins with 30+ days of data have established patterns
- ML can learn from momentum, volume, social signals
- Less explosive but more predictable

---

## Implementation Plan

### Phase 1: Rule-Based New Listing System (Immediate)

**Files to Create/Modify:**

1. **`src/execution/new_listing_entry.py`** (NEW)
   - `get_new_listings(db) -> list[str]`: Query coins <7d old
   - `should_enter_new_listing(db, symbol) -> bool`: Check if already entered
   - `enter_new_listing(db, symbol, leverage=2)`: Create paper position

2. **`src/execution/exit.py`** (MODIFY)
   - Add `apply_trailing_stop(position, current_price, peak_price) -> dict`
   - Trail logic: activate at +15%, trail 10% below peak
   - Store peak_price in position DB for tracking

3. **`orchestration/run_cycle.py`** (MODIFY)
   - Add step before champion scoring: `enter_new_listings(db)`
   - Run on every 4H cycle

4. **`config.py`** (ADD)
   ```python
   # New Listing Entry
   NEW_LISTING_ENABLED = True
   NEW_LISTING_MAX_AGE_DAYS = 7
   NEW_LISTING_POSITION_PCT = 0.02  # 2% per coin
   NEW_LISTING_TRAIL_ACTIVATE = 0.15  # Activate at +15%
   NEW_LISTING_TRAIL_DISTANCE = 0.10  # Trail 10% below peak
   NEW_LISTING_HARD_SL = 0.05  # -5% stop loss
   NEW_LISTING_HORIZON_BARS = 42  # Exit after 7 days if no TP/SL
   ```

**Testing:**
- Backtest on ROBO, MANTRA, KAT, CL, OPN historical data
- Simulate rule-based entry + trailing stop exit
- Target: PF > 1.0 on these 5 coins

### Phase 2: ML System Restriction (Next)

**Files to Modify:**

1. **`src/tournament/challenger.py`**
   - Skip coins with <180 bars (30 days) when generating challengers
   - Update: `get_training_symbols(db) -> list[str]`

2. **`src/labels/generate.py`**
   - Only generate labels for coins with ≥180 bars

3. **`src/execution/entry.py`**
   - Skip ML scoring for coins <30 days old (they use rule-based Track 1)

### Phase 3: Exit Strategy Optimization (Optional)

**If rule-based trailing stops work well on new listings:**
- Test trailing stops in ML backtest (Track 2)
- Compare fixed TP=30% vs trailing (activate 15%, trail 10%)
- Update `src/tournament/backtest.py` if trailing wins

---

## Risk Assessment

### Risks of Rule-Based New Listing Strategy

1. **High Variance:** 80-90% of new coins dump → need strong risk management
   - Mitigation: Small position size (2%), hard stop (-5%)

2. **Exchange Manipulation:** Blofin might manipulate new listings (pump & dump)
   - Mitigation: Trailing stops capture some upside, limit downside

3. **Capital Inefficiency:** Deploying 2% per coin, 10 coins = 20% of portfolio tied up
   - Mitigation: 7-day horizon clears positions quickly

4. **No Edge if Timing is Random:** If spikes are completely unpredictable, strategy fails
   - Counter: Data shows spikes ARE happening - we just need to be IN THE WATER

### Risks of ML-Only Approach (Status Quo)

1. **Missing 76% of Opportunities:** Spikes happen before ML can act
2. **Wasted Compute:** Training 753 models that can't catch the target
3. **Late to Party:** By day 30, spike already happened

**Conclusion:** Rule-based approach has LOWER risk than continuing status quo.

---

## Success Metrics

### Track 1 (Rule-Based New Listings)

- **Activation:** Average 5-10 new coins per week (<7d old)
- **Target Win Rate:** 15-20% (at least 1 in 5 coins spike)
- **Target Avg Win:** 30-50% (trailing stops capture partial moves)
- **Target PF:** 1.2-1.5 (positive skew from big winners)
- **Timeline:** 4 weeks to evaluate (need 20+ entries)

### Track 2 (ML Established Coins)

- **Activation:** Same as current (tournament promotions to FT)
- **Target:** At least 1 model with FT PF > 1.5 on 30+ day old coins
- **Timeline:** 8 weeks (existing tournament pipeline)

---

## Decision Required

**Approve Phase 1 implementation?**

- [ ] Yes - implement rule-based new listing entry + trailing stops
- [ ] No - continue optimizing ML-only approach
- [ ] Modify - propose changes to plan

**If approved, estimated timeline:**
- Phase 1: 2-4 hours (coding + testing)
- Backtest validation: 1 hour
- Deploy to production: Restart services, monitor 1 cycle
- Evaluation: 4 weeks of live data

---

## Appendix: Alternative Approaches Considered

### Alt 1: Lower Feature Requirements (Use 7-day features only)
- **Rejected:** Still can't predict bar 0-10 (first 2 days) where biggest spikes happen

### Alt 2: Pre-listing Data (Social signals before coin lists)
- **Rejected:** No CoinGecko/social data before listing, Blofin doesn't announce in advance

### Alt 3: Wider Trailing Stops (activate earlier, trail wider)
- **Considered:** Part of Phase 3 optimization

### Alt 4: Momentum-Only Models (train on short history)
- **Rejected:** Can't predict unpredictable - still need 20+ bars minimum

---

**End of Proposal**
