# Moonshot v2 Pivot — New Coin Long Spikes (2026-03-15)

## Context

Rob directive: "Change moonshot to look for bigger long spikes on newer coins, and just bigger moves in general."

Validation showed 45.5% of new coins (<30d) hit +30% within 7 days (5 of 11 in last month).

## Changes Made

### Config Updates (config.py)

| Parameter | Old | New | Reason |
|-----------|-----|-----|--------|
| `TP_PCT` | 0.10 (10%) | **0.30 (30%)** | Hunt bigger moves |
| `MIN_BT_PF_LONG` | 0.7 | **0.5** | Lower gate — moonshots are rare |
| `MIN_BT_PRECISION_LONG` | 0.22 | **0.15** | Expect many losers |
| `BOOTSTRAP_PF_LOWER_BOUND_LONG` | 0.6 | **0.4** | Asymmetric payoff (lose 5%, win 30%) |
| `LONG_DISABLED` | True | **False** | Enable longs (primary mission) |
| `MAX_LONG_POSITIONS` | 3 | **10** | Need more lottery tickets |
| `MAX_SHORT_POSITIONS` | 6 | **2** | Backup only |
| `NEW_LISTING_BOOST` | 1.5x | **5x** | Prioritize <30d coins |
| `ENTRY_THRESHOLD_FLOOR` | 0.70 | **0.50** | Lower entry bar for longs |
| `INVALIDATION_GRACE_BARS` | 2 (8h) | **20 (80h = 3.3d)** | Let longs run longer |

### Philosophy Updates

Created **MOONSHOT_GOALS.md** — full mission statement:
- Hunt 30%+ spikes on new coins (<30d old)
- Long-heavy (10 positions), shorts backup (2 positions)
- Expect 80% losers — only top 5 winners matter
- Differentiation from Blofin Stack (moonshots vs steady grind)

Updated **CORE_PHILOSOPHY.md**:
- FT is free, losers don't cost anything
- Expect 95% losers, find the 0.5-1% winners
- Never optimize for aggregate metrics

### Tournament Changes

**Promotion:**
- Long models: easier to enter FT (PF≥0.5, prec≥0.15)
- Short models: keep current champion, but STOP promoting new shorts

**Position management:**
- 10 long slots (up from 3) → more lottery tickets
- 2 short slots (down from 6) → minimal short exposure
- 5x boost for new listings → heavily favor <30d coins
- Entry threshold 0.50 (down from 0.70) → take more long shots

**Exit logic:**
- Invalidation grace 20 bars (3.3 days) → let longs breathe
- Keep tight 5% SL (limit damage on losers)
- Trail activates at 20% (same)

## Expected Outcomes

**Good:**
- 2-3 longs hit +30-50% per month
- 7-8 longs lose 5% (tight SL)
- Net: massively positive even with 80% loss rate
- Example: 3 wins at +35% = +105%, 7 losses at -5% = -35%, net +70%

**Timeline:**
- First cycle (4h): new challengers with lowered gates
- Week 1: 10 long positions fill, start collecting data
- Week 2-4: See if any hit +30% TP
- Month 1: Evaluate champion long PnL vs old short-heavy approach

## Monitoring

**Dashboard metrics to add:**
- New coin coverage (% of <30d coins we entered)
- Long champion PnL (separate from short)
- Top 5 long positions by PnL this month
- Coin age distribution of active positions

**Success criteria:**
- At least 1 position hits +30% in first month
- Long champion PnL > 0% after 50 trades
- New coin entry rate > 50% of available <30d coins

## Rollback Plan

If after 1 month:
- Zero longs hit +30%
- Long champion PnL < -20%
- New coins consistently fail

Then: Revert to short-heavy, keep new listing boost but lower TP back to 10-15%.

## Next Steps

1. ✅ Update config.py
2. ✅ Write MOONSHOT_GOALS.md
3. ✅ Update CORE_PHILOSOPHY.md
4. [ ] Restart moonshot-v2.service (pick up new config)
5. [ ] Watch first cycle — verify long models generate
6. [ ] Add new coin metrics to dashboard
7. [ ] Fix invalidation (lock features at entry) — separate card

---

*Committed 2026-03-15 08:45 MST*
