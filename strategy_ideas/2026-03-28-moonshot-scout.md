# Moonshot Strategy Scout — 2026-03-28

**Generated:** 2026-03-28 10:05 MST  
**Context:** 1 short champion (3.3% PnL, 71.3% WR), no long champion, 102 models in backtest queue

## Tournament State Analysis

### Champions
- **8bcea880b343** (short): LightGBM, no_social features, 94 FT trades, PF 3.12
- **new_listing**: Empty champion slot (0 trades)

### Recent Performance
- Long models: 23 active/champion, avg PnL -0.22%, avg PF 0.1 (STRUGGLING)
- Short models: 866 active/champion, avg PnL 0.0%, avg PF 5.79 (WORKING)
- Backtest queue: 102 models (53 long, 49 short)

### Failure Patterns
All recent retirements (20 sampled) failed at backtest stage — not reaching FT. This suggests:
- Backtest gate is working correctly (95%+ rejection is expected)
- Need more diversity in feature combinations to find edge
- Long side needs special attention (underperforming)

## Gap Analysis

### 1. Long Side Crisis
- Only 23 long models in FT/champion vs 866 short
- Avg PF 0.1 vs 5.79 for short
- HYPOTHESIS: Long setups need different features (support bounces, mean reversion, breakouts)

### 2. Underutilized Feature Combos
**Momentum Extremes:**
- momentum_4w/8w exist but not combined with funding_rate_extreme + oi_change_24h for blow-off detection

**Breakout Detection:**
- higher_highs + distance_from_resistance + volume_spike not tested together
- Could catch early trend acceleration

**Mean Reversion:**
- consec_down_bars + distance_from_support + atr_compression for oversold bounces (LONG bias)
- consec_up_bars + distance_from_resistance + funding_rate_extreme for exhaustion (SHORT bias)

**Volatility Regime Adaptation:**
- atr_percentile + realized_vol_ratio + bb_squeeze_pct as regime filter
- Different features work in high vs low vol environments

**BTC Beta Plays:**
- btc_30d_return + market_breadth + coin momentum for correlation trades
- Identify coins that outperform/underperform BTC moves

### 3. Algorithm Diversity
- Champion is LightGBM
- Queue has many XGBoost (likely)
- Need more CatBoost experiments (handles categoricals differently)
- Try lower tree counts (50-100) for less overfitting

### 4. Hyperparameter Exploration
- neg_class_weight: Champion uses 8, try 3-5 for more aggressive entries
- confidence_threshold: Champion 0.4, try 0.5-0.6 for higher precision
- learning_rate: Try 0.005-0.01 (slower, more stable) vs 0.1+ (fast, aggressive)

## Proposed Variants (10 Models)

### 1. LONG Mean Reversion Extreme
**Hypothesis:** Oversold bounces on support with compressed volatility  
**Features:** consec_down_bars, distance_from_support, atr_compression, bb_squeeze_pct, volume_ratio_3d, momentum_1d, btc_30d_return  
**Model:** XGBoost, low learning_rate (0.01), high neg_class_weight (10), low confidence (0.35)

### 2. SHORT Exhaustion Fade
**Hypothesis:** Parabolic moves exhaust when funding + OI extreme + consecutive up bars  
**Features:** consec_up_bars, distance_from_resistance, funding_rate_extreme, oi_change_24h, volume_spike, momentum_1d, momentum_3d  
**Model:** LightGBM (like champion), neg_class_weight 5, confidence 0.5

### 3. LONG Breakout Acceleration
**Hypothesis:** Higher highs + volume spike + breaking resistance = trend start  
**Features:** higher_highs, distance_from_resistance, volume_spike, volume_ratio_7d, momentum_4w, btc_30d_return, atr_percentile  
**Model:** CatBoost, learning_rate 0.05, depth 5, confidence 0.45

### 4. SHORT BTC Beta Bear
**Hypothesis:** When BTC dumps, high-beta alts dump harder  
**Features:** btc_30d_return, market_breadth, momentum_8w, funding_rate_7d_avg, oi_percentile_90d, volume_ratio_7d  
**Model:** XGBoost, max_depth 4, neg_class_weight 7, confidence 0.5

### 5. LONG Volatility Compression Coil
**Hypothesis:** Low vol → big move (long bias if support holding)  
**Features:** atr_compression, bb_squeeze_pct, realized_vol_ratio, distance_from_support, volume_ratio_3d, consec_down_bars  
**Model:** LightGBM, num_leaves 31, learning_rate 0.02, confidence 0.4

### 6. SHORT High Vol Reversal
**Hypothesis:** Extreme vol spikes often precede reversals (short at resistance)  
**Features:** atr_percentile, realized_vol_ratio, high_low_range_pct, distance_from_resistance, volume_spike, momentum_1d  
**Model:** XGBoost, n_estimators 150, learning_rate 0.03, confidence 0.55

### 7. LONG Minimal Core (5 features)
**Hypothesis:** Less is more — avoid overfitting with tiny feature set  
**Features:** price_vs_52w_low, momentum_4w, volume_ratio_7d, atr_percentile, btc_30d_return  
**Model:** XGBoost, n_estimators 100, max_depth 3, confidence 0.45

### 8. SHORT Minimal Core (5 features)
**Hypothesis:** Mirror of #7 but for shorts  
**Features:** price_vs_52w_high, momentum_8w, funding_rate_extreme, oi_change_24h, bb_position  
**Model:** LightGBM, num_leaves 15, neg_class_weight 6, confidence 0.5

### 9. LONG Extended Data Full Arsenal
**Hypothesis:** Use ALL extended features for max information (if available)  
**Features:** All core + all extended (no social) — 38 features  
**Model:** CatBoost, depth 6, learning_rate 0.01, confidence 0.5

### 10. SHORT OI Divergence Specialist
**Hypothesis:** OI rising + price falling = short squeeze setup (fade it)  
**Features:** oi_price_divergence, oi_change_24h, oi_change_7d, funding_rate_current, price_change_24h_pct, volume_ratio_3d  
**Model:** XGBoost, max_depth 4, neg_class_weight 8, confidence 0.6

## Implementation Notes

- All variants use no_social feature_set (DISABLE_SOCIAL_FEATURES=true in config)
- Confidence thresholds calibrated based on direction (longs slightly lower for more opportunities)
- Heavy focus on LONG variants (6 of 10) to address long-side crisis
- Mix of minimal (5-7 features) and comprehensive (38 features) to test complexity vs simplicity
- Algorithm diversity: 5 XGBoost, 3 LightGBM, 2 CatBoost

## Expected Outcomes

- 95%+ will retire at backtest stage (EXPECTED, tournament philosophy)
- 1-2 might reach FT if lucky
- Goal: Find 1 new angle that generates edge, especially on LONG side
- Even failures teach us what doesn't work (feature combos to avoid)
