# Moonshot v2 — Mission & Goals

**Updated 2026-03-15** — Full pivot to new coin long spikes

## Primary Mission

**Hunt for 30%+ price spikes on new crypto listings.**

Target: New coins (<30 days old) that pump 30-50%+ within 7 days.

## Why This Works (Validation)

**Last 30 days:** 11 new coins listed, 5 hit +30% (45.5% success rate)
- ROBO-USDT: +44.3%
- MANTRA-USDT: +39.3%
- KAT-USDT: +30.6%
- CL-USDT: +30.1%
- OPN-USDT: +30.1%

This is 10x better than trying to predict consistent money on established coins (that's Blofin Stack's job).

## Strategy

**Long-heavy, new listing focused:**
- Run 8-10 long positions concurrently (up from 3)
- 5x boost for coins <30 days old (up from 1.5x)
- Lower entry threshold for longs (0.50 vs 0.70)
- Target +30% TP (up from +10%)
- Keep tight 5% SL

**Shorts: backup only**
- Keep short champion running (it's working: 2.22 PF, 388 trades)
- Stop promoting new short models
- Max 2 short positions (down from 6)

## What Success Looks Like

**Good:**
- 2-3 long positions hit +30-50% per month
- Rest lose 5% (tight SL limits damage)
- Net: massively positive even with 80% loss rate

**Bad:**
- Trying to make all longs profitable
- Optimizing for aggregate win rate
- Micromanaging exits

## Difference from Blofin Stack

| Moonshot v2 | Blofin Stack |
|-------------|--------------|
| Hunt big spikes (30-50%) | Grind consistent profit (5-15%) |
| New coins (<30d preferred) | Established coins |
| Lower leverage (2x) | Higher leverage (3-5x) |
| 8-10 positions | 20-50 positions |
| Infrequent but huge wins | Frequent small wins |

## Tournament Philosophy

**Generate 100+ long model variants per day:**
- Random feature subsets (price_heavy, volatility_heavy, social_boost, etc.)
- Random hyperparameters
- Let them compete in FT (20-200 trades)

**Promote ruthlessly:**
- Only top FT PnL becomes champion
- Ignore aggregate metrics
- Expect 95% of models to lose money — that's normal

**Fix invalidation:**
- Lock features at entry (prevent drift)
- 50-trade grace period before invalidation kicks in
- Let models prove profitability before killing them

## Metrics That Matter

**System-level:**
- Champion long PnL (total % return)
- Top 5 long positions by PnL this month
- New coin coverage (% of <30d coins we entered)

**Ignore:**
- System-wide win rate
- Average PF across all models
- FT backlog size

## Implementation Checklist

- [x] Validate new coin longs are viable (45.5% hit +30%)
- [ ] Update config.py (raise long positions, boost, TP target)
- [ ] Disable new short model promotion
- [ ] Fix invalidation (lock features at entry)
- [ ] Add "new listing age" to dashboard
- [ ] Track new coin coverage metric

---

*"Hunt the moonshots. Let Blofin Stack grind the steady money."*
