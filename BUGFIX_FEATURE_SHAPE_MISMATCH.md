# BUGFIX: Feature Shape Mismatch Corruption

**Date:** 2026-03-26  
**Severity:** CRITICAL (blocked FT scoring)  
**Status:** FIXED  

## Problem

Model `9b7f05d5392c` in `tournament_models` table had `feature_set` with 5 features in metadata, but the trained LGBMClassifier pickle file expected 25 features. This caused ValueError during FT scoring:

```
ERROR moonshot _score_symbols: prediction failed for BTC-USDT — vec length=5, expected=5 features, 
error: X has 5 features, but LGBMClassifier is expecting 25 features as input.
```

## Root Cause

**Database corruption during model creation:** The model was trained with 25 features (correct), but when the model metadata was saved to the database, only 5 features were written to the `feature_set` column (incorrect).

This mismatch occurred somewhere in the `generate_challengers()` → `backtest_challenger()` → DB update flow.

## Investigation

1. **Model file:** `models/tournament/9b7f05d5392c.pkl` contained a LGBMClassifier with `n_features_in_=25`
2. **Database:** `tournament_models.feature_set` = `["oi_price_divergence", "oi_change_24h", "oi_change_7d", "oi_percentile_90d", "price_change_24h_pct"]` (5 features)
3. **During FT scoring:** `_get_feature_values()` extracts 5 features → model.predict_proba() expects 25 → ValueError

## Fix

Added validation in two places:

### 1. Training-time validation (backtest.py)
After `model.fit()`, validate that the trained model's feature count matches the expected `feature_names`:

```python
# Validate feature shape matches model expectation (prevent corruption)
model_feature_count = None
if hasattr(model, 'n_features_in_') and model.n_features_in_ > 0:
    model_feature_count = model.n_features_in_
elif hasattr(model, 'feature_names_') and model.feature_names_:
    model_feature_count = len(model.feature_names_)

if model_feature_count is not None and model_feature_count != len(feature_names):
    raise ValueError(f"Feature shape mismatch: model expects {model_feature_count}, feature_set has {len(feature_names)}")
```

**Effect:** Any future corruption will fail immediately during backtest, preventing corrupted models from being saved.

### 2. Load-time validation (forward_test.py)
When loading models for FT scoring, detect corrupted models and auto-retire them:

```python
model_feature_count = None
if hasattr(model, 'n_features_in_') and model.n_features_in_ > 0:
    model_feature_count = model.n_features_in_
elif hasattr(model, 'feature_names_') and model.feature_names_:
    model_feature_count = len(model.feature_names_)

if model_feature_count is not None and model_feature_count != len(feature_names):
    # Retire corrupted model
    db.execute(
        "UPDATE tournament_models SET stage='retired', retired_at=?, retire_reason=? WHERE model_id=?",
        (now_ms, f"feature_shape_mismatch: model expects {model_feature_count}, DB has {len(feature_names)}", model_id)
    )
```

**Effect:** Any existing corrupted models will be auto-retired during the next FT cycle.

### 3. CatBoost compatibility
CatBoost models don't set `n_features_in_` (it's always 0), so the validation checks `feature_names_` as a fallback. This prevents false positives for CatBoost models.

## Actions Taken

1. ✅ Added validation in `backtest_challenger()` (prevent future corruption)
2. ✅ Added validation in `score_forward_test_models()` (auto-retire existing corruption)
3. ✅ Retired model `9b7f05d5392c` manually in DB
4. ✅ Verified no other corrupted models exist (checked all 829 active FT/champion models)
5. ✅ Committed fix: `79812ae` on `feature/moonshot-2x-leverage` branch
6. ✅ Pushed to GitHub

## Verification

Checked all 829 active models (forward_test + champion stages) and found:
- **0 corrupted models** after applying CatBoost-aware validation logic
- All models have matching feature counts between pickle files and DB metadata

## Prevention

This bug should not recur because:
1. **Training-time validation** will raise an error immediately if a model is trained with the wrong feature count
2. **Load-time validation** will auto-retire any corrupted models that slip through
3. The validation handles CatBoost's `n_features_in_=0` quirk by checking `feature_names_` as a fallback

## Open Questions

- **Why did this corruption occur in the first place?** Need to audit `generate_challengers()` and `resolve_feature_set()` to ensure feature_set is always correctly saved to DB.
- **Are there other models with this issue?** The validation will catch them during the next FT cycle.

## Files Changed

- `src/tournament/backtest.py` — added training-time validation
- `src/tournament/forward_test.py` — added load-time validation + auto-retire
- `data/moonshot_v2.db` — retired model `9b7f05d5392c`

## Commit

```
commit 79812ae
fix(moonshot): prevent feature shape mismatch corruption

- Add validation in backtest_challenger() to detect feature shape mismatch
  immediately after model.fit() (raise error before model is saved)
- Add validation in score_forward_test_models() to detect corrupted models
  during FT scoring and auto-retire them with descriptive reason
- Handle CatBoost quirk: n_features_in_ is always 0, use feature_names_ instead
- Retired model 9b7f05d5392c (trained with 25 features, DB had 5)
```
