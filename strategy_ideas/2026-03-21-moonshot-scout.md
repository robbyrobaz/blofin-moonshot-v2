# Moonshot Strategy Scout — March 21, 2026

## Tournament Analysis

### Current State
- **Total models:** 2,784 (all created in last 24h — mass generation active)
- **Champions:** 2 (1 short, 1 new_listing placeholder)
  - `de44f72dbb01` (short): CatBoost, "all" features, FT PF 2.22, PnL 0.68% over 388 trades
- **FT models:** 0 (all new challengers in backtest phase)
- **Recent retirements (7d):** 2,187
  - Main failures: backtest_failed (95%), ft_unprofitable_pf_below_0.9 (3%)

### Champion Analysis
**de44f72dbb01** (short champion):
- Model: CatBoost (depth 8, 100 estimators, LR 0.01)
- Features: ALL (50 features — core + extended + social)
- Class weight: 8:1 (negative/positive)
- Confidence threshold: 0.7
- Performance: 2.22 PF, 0.68% PnL, 388 trades

**Key Insight:** Champion uses ALL features (maximal approach) — suggests we need MORE feature diversity, not less.

### Recent Retirement Patterns
- Model type distribution: Balanced (CatBoost 711, LightGBM 741, XGBoost 735)
- Backtest failure rate: 95% (expected per tournament philosophy)
- Error pattern: "could not convert string to float: 'price_vs_52w_high'" (10 models) — data pipeline bug?

## Identified Gaps

### 1. Feature Experimentation Gaps
- **Time horizons:** Current features are 52w/4w/8w/7d — missing 1h/4h/1d short-term signals
- **Cross-coin correlation:** No features comparing coin vs sector/market
- **Liquidity signals:** Missing bid-ask spread, order book depth
- **Momentum regime interaction:** Not testing price momentum × volatility regime combinations

### 2. Hyperparameter Gaps
- **Class weight extremes:** Current 3-10 range — test 1-2 (balanced) and 15-20 (aggressive)
- **Depth exploration:** Max depth 10 — test 12-15 for complex interactions
- **Ensemble diversity:** All boosting — missing stacking/voting ensembles

### 3. Feature Subset Gaps
Looking at challenger.py, we have good preset coverage:
- ✅ Preset features (all, core_only, price_volume, no_social, extended_only)
- ✅ Random focus areas (price_heavy, volume_heavy, volatility_heavy, regime_aware, social_boost, minimal, maximal)
- ⚠️ Missing: **temporal windowing** (1h vs 1d vs 1w features for same indicator)
- ⚠️ Missing: **regime-conditional subsets** (different features for high vol vs low vol)

## Strategy Variants (8 experiments)

### Batch 1: Temporal Windowing (3 variants)
**Hypothesis:** Different lookback windows capture different alpha signals.

1. **ultra_short_term** (12-18 features)
   - Focus: 1h/4h momentum, volume spikes, funding rate changes
   - Features: price_change_24h_pct, vol_24h_vs_7d_avg, funding_rate_current, volume_spike, atr_compression
   - Target: Capture intraday mean reversion

2. **medium_term_balanced** (20-25 features)
   - Focus: 7d/30d trends + current volatility
   - Features: momentum_4w, volume_ratio_7d, btc_30d_return, oi_change_7d, bb_position
   - Target: Capture weekly cycles

3. **long_term_structural** (15-20 features)
   - Focus: 52w price levels, market regime, social trends
   - Features: price_vs_52w_high/low, btc_vol_percentile, fear_greed_7d_change, github_commits_7d
   - Target: Capture macro regime shifts

### Batch 2: Extreme Hyperparameters (2 variants)
**Hypothesis:** Current param space is too conservative.

4. **aggressive_imbalance** (CatBoost)
   - Class weight: 20 (vs current max 10)
   - Depth: 12 (vs current max 10)
   - Learning rate: 0.005 (slower, more careful)
   - Features: all
   - Target: Catch rare high-conviction signals

5. **ultra_fast_shallow** (LightGBM)
   - Estimators: 50 (vs current min 100)
   - Depth: 3 (vs current min 4)
   - Learning rate: 0.2 (vs current max 0.1)
   - Features: minimal (10-15)
   - Target: Simple fast models that don't overfit

### Batch 3: Interaction-Focused (2 variants)
**Hypothesis:** Feature interactions matter more than individual features.

6. **volatility_regime_conditioned**
   - Features: [atr_percentile, btc_vol_percentile] × [momentum_4w, volume_spike, funding_rate_extreme]
   - Implementation: Two separate models trained on high/low vol regimes
   - Target: Regime-specific signals

7. **social_momentum_fusion** (18-22 features)
   - Features: social signals (fear_greed, coingecko_trending, news_velocity) + price momentum (momentum_4w/8w, higher_highs)
   - NO volume/OI features
   - Target: Capture narrative-driven pumps

### Batch 4: Data Quality Experiments (1 variant)
**Hypothesis:** Some models fail due to missing extended features (30+ day lag).

8. **core_only_robust** (25 features)
   - Features: ONLY core (no extended, no social)
   - Purpose: Baseline for coins with <30 days data
   - Model: XGBoost (depth 6, 200 estimators)
   - Target: Stable performance across all coins

## Implementation Plan

### Phase 1: Write Variant Configs (Subagent)
Spawn Codex to generate 8 JSON config files in `configs/generated/2026-03-21-scout-*.json`:
- Each file defines: model_type, params, feature_set (list), direction (long/short balanced)
- Follow challenger.py format (see existing params structure)

### Phase 2: Queue Insertion (Direct SQL)
Insert 8 new models into tournament_models:
```sql
INSERT INTO tournament_models
  (model_id, direction, stage, model_type, params, feature_set, entry_threshold, created_at)
VALUES
  (sha256_hash(config), 'short', 'backtest', 'catboost', json_params, json_features, 0.5, now_ms);
```

### Phase 3: Validation
- Verify configs don't break feature resolution
- Check backtest queue accepts new models
- Confirm next cycle will process them

## Expected Outcomes

- **Success:** 1-2 of 8 variants reach FT (12-25% pass rate)
- **Discovery:** Identify which temporal window or hyperparameter extreme works
- **Learning:** Document which feature combinations fail (update TOURNAMENT_PHILOSOPHY.md)

## Risk Mitigation

- All variants use existing feature infrastructure (no pipeline changes)
- Configs stored in git (reversible)
- If subagent fails, manually implement 2-3 highest-value variants
- Tournament cycle will naturally filter out failures

---

**Next Steps:**
1. Spawn Codex subagent to write 8 config JSONs
2. Insert models via SQL
3. Commit configs to git
4. Send Telegram summary
