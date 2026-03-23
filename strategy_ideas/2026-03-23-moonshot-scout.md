# Moonshot Strategy Scout — 2026-03-23

**Generated:** 2026-03-23 10:00 AM MST  
**Tournament Analysis Date:** Mar 23 2026

## Tournament State Analysis

### Champions (Current)
1. **SHORT Champion:** `de44f72dbb01` (CatBoost)
   - FT_PF: 2.22, FT_PnL: 0.68%, FT_trades: 388
   - Feature set: `all` (50 features including social)
   - Config: lr=0.01, depth=8, n_est=100, neg_weight=8

2. **New Listing:** `rule_based` (0 trades, waiting)

### Queue Status
- Backtest queue: 8 models
- Backtest stage: 15 models
- Forward test: 694 models (most losing)
- Retired: 2,406 models

### Performance Patterns
- **Best feature sets by avg BT PF:**
  - `extended_only`: 0.982 (11 models)
  - `all`: 0.978 (16 models)
  - `price_volume`: 0.970 (15 models)
  - `core_only`: 0.955 (33 models)
  - `no_social`: 0.944 (22 models)

- **Model type distribution (FT stage):**
  - XGBoost: 260 models, avg FT PnL: -0.027%
  - LightGBM: 235 models, avg FT PnL: -0.002%
  - CatBoost: 199 models, avg FT PnL: -0.025%

- **Only 1 profitable FT model** out of 694 (0.14% success rate — tournament working as intended)

### Identified Gaps

1. **CatBoost underexplored** — only 1 champion, but competitive FT performance
2. **Feature subsets promising** — `core_only` and `extended_only` have high BT PF with fewer features
3. **Hyperparameter diversity lacking** — most models use similar depth/learning rate
4. **No explicit regime filters** — high_vol vs low_vol, trending vs ranging
5. **Short-only bias** — 1 short champion performing, need more long experimentation

---

## Proposed Variants (8 models)

### 1. **CatBoost Depth Sweep (Short)**
**Hypothesis:** Current champion uses depth=8. Test shallower trees for better generalization.

```json
{
  "model_type": "catboost",
  "direction": "short",
  "feature_set": "all",
  "learning_rate": 0.01,
  "max_depth": 6,
  "n_estimators": 150,
  "neg_class_weight": 10,
  "num_leaves": 31,
  "confidence_threshold": 0.70
}
```

**Rationale:** Depth=6 + more estimators for smoother learning. Increase neg_weight to 10 for more conservative short entries.

---

### 2. **CatBoost Fast Learner (Short)**
**Hypothesis:** Higher LR + fewer estimators for faster adaptation to regime changes.

```json
{
  "model_type": "catboost",
  "direction": "short",
  "feature_set": "all",
  "learning_rate": 0.05,
  "max_depth": 8,
  "n_estimators": 50,
  "neg_class_weight": 8,
  "num_leaves": 63,
  "confidence_threshold": 0.75
}
```

**Rationale:** 5x faster learning, half the trees. Higher confidence threshold to compensate for potential overfitting.

---

### 3. **LightGBM Core Features Only (Short)**
**Hypothesis:** 33 models with `core_only` averaging 0.955 BT PF. Drop extended/social noise.

```json
{
  "model_type": "lightgbm",
  "direction": "short",
  "feature_set": "core_only",
  "learning_rate": 0.02,
  "max_depth": 7,
  "n_estimators": 100,
  "neg_class_weight": 12,
  "num_leaves": 63,
  "confidence_threshold": 0.72
}
```

**Rationale:** Core features (25 total) = price action, volume, volatility, structure, BTC regime. Simpler signal, less overfitting risk.

---

### 4. **XGBoost Extended Features Only (Short)**
**Hypothesis:** 11 models with `extended_only` averaging 0.982 BT PF (highest). Test funding/OI/mark signals alone.

```json
{
  "model_type": "xgboost",
  "direction": "short",
  "feature_set": "extended_only",
  "learning_rate": 0.015,
  "max_depth": 6,
  "n_estimators": 120,
  "neg_class_weight": 10,
  "confidence_threshold": 0.68
}
```

**Rationale:** Extended features (12 total) = funding, OI, mark spread, 24h ticker. Derivative market signals for short bias.

---

### 5. **LightGBM Long Experiment (Core + Extended)**
**Hypothesis:** Long direction underperforming. Try conservative long setup with high neg_weight.

```json
{
  "model_type": "lightgbm",
  "direction": "long",
  "feature_set": ["core", "extended"],
  "learning_rate": 0.01,
  "max_depth": 6,
  "n_estimators": 150,
  "neg_class_weight": 15,
  "num_leaves": 31,
  "confidence_threshold": 0.75
}
```

**Rationale:** Long needs higher precision. Depth=6, high neg_weight (15), high confidence (0.75) for quality over quantity.

---

### 6. **CatBoost Price + Volume Only (Short)**
**Hypothesis:** Minimal feature set focusing on price action + volume. Test if we're overfitting with 50 features.

```json
{
  "model_type": "catboost",
  "direction": "short",
  "feature_set": ["price_vs_52w_high", "price_vs_52w_low", "momentum_4w", "momentum_8w", "bb_squeeze_pct", "bb_position", "volume_ratio_7d", "volume_ratio_3d", "obv_slope", "volume_spike", "volume_trend"],
  "learning_rate": 0.02,
  "max_depth": 7,
  "n_estimators": 100,
  "neg_class_weight": 8,
  "num_leaves": 63,
  "confidence_threshold": 0.70
}
```

**Rationale:** 11 features only (6 price action + 5 volume). If this works, we drop 39 noisy features.

---

### 7. **XGBoost High Volatility Regime (Short)**
**Hypothesis:** Test model tuned for high-vol environments (atr_percentile, realized_vol_ratio, btc_vol_percentile).

```json
{
  "model_type": "xgboost",
  "direction": "short",
  "feature_set": "all",
  "learning_rate": 0.02,
  "max_depth": 9,
  "n_estimators": 80,
  "neg_class_weight": 6,
  "confidence_threshold": 0.65
}
```

**Rationale:** Lower neg_weight (6) for more aggressive entries in volatile conditions. Deeper trees (9) to capture regime interactions.

---

### 8. **LightGBM Balanced Ensemble (Short)**
**Hypothesis:** Mid-range hyperparameters to find sweet spot between fast/slow learners.

```json
{
  "model_type": "lightgbm",
  "direction": "short",
  "feature_set": "no_social",
  "learning_rate": 0.025,
  "max_depth": 7,
  "n_estimators": 100,
  "neg_class_weight": 9,
  "num_leaves": 63,
  "confidence_threshold": 0.70
}
```

**Rationale:** `no_social` (37 features) = all except 13 social features. Mid-tier hyperparams for balanced risk/reward.

---

## Implementation Plan

1. **Write configs** to `configs/generated/2026-03-23-scout-01.json` through `08.json`
2. **Insert into backtest queue** via SQL
3. **Let tournament process** — backtest gate will filter, FT will validate
4. **Commit to git** — track all generated configs

## Expected Outcomes

- **2-3 models** pass backtest gate (PF ≥ 0.5, precision ≥ 0.15, trades ≥ 50)
- **0-1 models** survive FT and reach champion consideration (0.5% win rate expected)
- **Learning:** Which feature subsets/hyperparams work in current market regime

---

**Next Steps:**
1. Spawn coding subagent to write configs
2. Verify configs don't break pipeline (JSON schema validation)
3. Add to backtest queue
4. Commit to git
5. Monitor next tournament cycle
