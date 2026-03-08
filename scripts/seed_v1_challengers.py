"""Seed v2 tournament with v1's best forward-test model configurations.

V1 models were trained on a different feature set (17 features) with different
TP/SL targets (8%/10%) than v2 (15%/5%). We cannot use v1's .pkl files directly.

Instead, this script:
1. Reads all 15 v1 forward-test models from the v1 DB
2. Maps their LightGBM hyperparameters to the nearest valid v2 param-space values
3. Maps v1 feature selections to the best-matching v2 feature_set
4. Inserts unique configs as stage='backtest' challengers in v2's DB
5. Optionally generates feature-set variants for top models (bt_pf >= threshold)

The v2 backtest pipeline will then retrain and re-evaluate each seeded config
using v2's features + path-dependent labels. If a config passes the v2 gates
(PF>=1.3, precision>=0.25, trades>=50, bootstrap CI>=0.8 on fold 3), it gets
promoted to v2's forward-test arena.

This is especially valuable because:
- V2's FT arena currently has 19 short-only models (no longs!)
- V1's top models include strong long-direction configurations
- V1's discovered hyperparameter combinations (lr, leaves, depth, neg_weight)
  are validated signal-finders that are worth re-testing on v2's label scheme
"""

import hashlib
import json
import sqlite3
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
V1_DB_PATH = "/home/rob/.openclaw/workspace/blofin-moonshot/data/moonshot.db"
V2_DB_PATH = str(REPO_ROOT / "data" / "moonshot_v2.db")

# ---------------------------------------------------------------------------
# Feature mapping: v1 feature name → closest v2 feature name (or None=drop)
# ---------------------------------------------------------------------------
V1_TO_V2_FEATURE = {
    "price_vs_52w_high":  "price_vs_52w_high",   # exact match
    "atr_percentile":     "atr_percentile",        # exact match
    "bb_squeeze_pct":     "bb_squeeze_pct",        # exact match
    "bb_squeeze_duration":"bb_squeeze_pct",        # closest v2 equiv
    "volume_ratio":       "volume_ratio_7d",       # closest v2 equiv
    "volume_momentum_4h": "volume_ratio_3d",       # closest v2 equiv
    "obv_divergence":     "obv_slope",             # closest v2 equiv
    "new_listing_age":    "days_since_listing",    # closest v2 equiv
    "funding_rate":       "funding_rate_current",  # closest v2 equiv
    "open_interest_chg":  "oi_change_24h",         # closest v2 equiv
    # V1 features NOT available in v2 — dropped
    "max_leverage":           None,
    "exchange_volume_rank":   None,
    "liquidation_pressure":   None,
    "ls_ratio":               None,
    "ls_ratio_change":        None,
    "market_cap_tier":        None,
    "orderbook_imbalance":    None,
}

# V2 extended features (require 30+ days of API data)
_V2_EXTENDED = {
    "funding_rate_current", "funding_rate_7d_avg", "funding_rate_extreme",
    "oi_change_24h", "oi_change_7d", "oi_price_divergence", "oi_percentile_90d",
    "mark_index_spread",
    "price_vs_24h_high", "price_vs_24h_low", "vol_24h_vs_7d_avg", "price_change_24h_pct",
}

# V2 price/volume-only features (subset of core)
_V2_PRICE_VOLUME = {
    "price_vs_52w_high", "price_vs_52w_low",
    "momentum_4w", "momentum_8w",
    "bb_squeeze_pct", "bb_position",
    "volume_ratio_7d", "volume_ratio_3d",
    "obv_slope", "volume_spike", "volume_trend",
    "btc_30d_return", "btc_vol_percentile", "market_breadth",
    "days_since_listing", "is_new_listing",
}

# ---------------------------------------------------------------------------
# Hyperparameter mapping helpers
# ---------------------------------------------------------------------------

def _nearest(value, choices):
    return min(choices, key=lambda x: abs(x - value))


def map_learning_rate(lr: float) -> float:
    return _nearest(lr, [0.01, 0.05, 0.1])


def map_num_leaves(nl: int) -> int:
    if nl < 0:
        return 31  # v1 uses -1 for unlimited; default to 31 in v2
    return _nearest(nl, [31, 63, 127])


def map_max_depth(md: int) -> int:
    if md < 0:
        return 6  # v1 uses -1 for unlimited; use moderate depth in v2
    return _nearest(md, [4, 6, 8, 10])


def map_neg_class_weight(nw: float) -> int:
    return _nearest(nw, [3, 5, 8, 10])


def map_n_estimators(n: int) -> int:
    return _nearest(n, [100, 200, 500])


def map_confidence_threshold(thresh: float) -> float:
    return _nearest(thresh, [0.30, 0.40, 0.50, 0.60, 0.70])


def map_feature_set(v1_features: list[str]) -> str:
    """Determine best v2 feature_set for a list of v1 features."""
    mapped = {V1_TO_V2_FEATURE.get(f) for f in v1_features}
    mapped.discard(None)

    # If any extended features needed, use no_social
    if mapped & _V2_EXTENDED:
        return "no_social"

    # If all features are in price_volume subset, use price_volume
    if mapped and mapped.issubset(_V2_PRICE_VOLUME):
        return "price_volume"

    return "core_only"


# ---------------------------------------------------------------------------
# Core conversion
# ---------------------------------------------------------------------------

def convert_v1_params(v1_row: sqlite3.Row) -> dict:
    """Convert a v1 tournament_models row to a v2-compatible params dict."""
    raw = json.loads(v1_row["params"]) if v1_row["params"] else {}

    # V1 stored features under either "features" or "feature_subset" key
    v1_features = raw.get("features") or raw.get("feature_subset") or []

    lr        = raw.get("learning_rate", 0.05)
    num_leaves = raw.get("num_leaves", 31)
    max_depth  = raw.get("max_depth", 6)
    neg_weight = raw.get("neg_weight", 3.0)
    n_est      = raw.get("n_estimators", 100)
    threshold  = float(v1_row["threshold"])
    direction  = v1_row["direction"]

    return {
        "model_type":          "lightgbm",
        "direction":           direction,
        "learning_rate":       map_learning_rate(lr),
        "n_estimators":        map_n_estimators(n_est),
        "num_leaves":          map_num_leaves(num_leaves),
        "max_depth":           map_max_depth(max_depth),
        "neg_class_weight":    map_neg_class_weight(neg_weight),
        "confidence_threshold": map_confidence_threshold(threshold),
        "feature_set":         map_feature_set(v1_features),
    }


def make_model_id(params: dict) -> str:
    blob = json.dumps(params, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Variant generation for top-performing v1 configs
# ---------------------------------------------------------------------------

_FEATURE_SETS = ["core_only", "price_volume", "no_social", "all"]


def generate_variants(base_params: dict, bt_pf: float) -> list[dict]:
    """For high-BT-PF v1 models (bt_pf >= 5.0), generate one variant per
    feature_set to maximize coverage. For weaker models, just use base."""
    if bt_pf < 5.0:
        return [base_params]

    variants = []
    for fs in _FEATURE_SETS:
        v = dict(base_params)
        v["feature_set"] = fs
        variants.append(v)
    return variants


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def seed_challengers(dry_run: bool = False):
    # ── Load v1 FT models ──────────────────────────────────────────────────
    v1_db = sqlite3.connect(V1_DB_PATH)
    v1_db.row_factory = sqlite3.Row
    v1_models = v1_db.execute(
        """SELECT model_id, direction, threshold, params, bt_pf, bt_precision, bt_trades
           FROM tournament_models
           WHERE stage = 'forward_test'
           ORDER BY bt_pf DESC"""
    ).fetchall()
    v1_db.close()

    print(f"V1 forward-test models found: {len(v1_models)}")
    print()

    # ── Connect to v2 DB ───────────────────────────────────────────────────
    v2_db = sqlite3.connect(V2_DB_PATH)
    v2_db.row_factory = sqlite3.Row
    now_ms = int(time.time() * 1000)

    inserted = 0
    skipped_dup = 0
    total_candidates = 0

    for v1_row in v1_models:
        v1_id   = v1_row["model_id"]
        v1_pf   = float(v1_row["bt_pf"] or 0.0)
        v1_prec = float(v1_row["bt_precision"] or 0.0)
        v1_dir  = v1_row["direction"]

        base_params = convert_v1_params(v1_row)
        candidates  = generate_variants(base_params, v1_pf)
        total_candidates += len(candidates)

        print(f"V1 {v1_id} ({v1_dir}) bt_pf={v1_pf:.2f} prec={v1_prec:.0%} "
              f"→ {len(candidates)} candidate(s):")

        for params in candidates:
            model_id = make_model_id(params)

            # Check duplicate
            exists = v2_db.execute(
                "SELECT 1 FROM tournament_models WHERE model_id = ?",
                (model_id,),
            ).fetchone()

            if exists:
                print(f"  SKIP {model_id} (already in v2 DB) "
                      f"[fs={params['feature_set']}]")
                skipped_dup += 1
                continue

            print(f"  INSERT {model_id} dir={params['direction']} "
                  f"fs={params['feature_set']} "
                  f"lr={params['learning_rate']} leaves={params['num_leaves']} "
                  f"depth={params['max_depth']} neg={params['neg_class_weight']} "
                  f"n_est={params['n_estimators']} thresh={params['confidence_threshold']}")

            if not dry_run:
                v2_db.execute(
                    """INSERT INTO tournament_models
                       (model_id, direction, stage, model_type, params, feature_set,
                        entry_threshold, created_at)
                       VALUES (?, ?, 'backtest', ?, ?, ?, ?, ?)""",
                    (
                        model_id,
                        params["direction"],
                        params["model_type"],
                        json.dumps(params, sort_keys=True),
                        params["feature_set"],
                        params["confidence_threshold"],
                        now_ms,
                    ),
                )
                inserted += 1

        print()

    if not dry_run:
        v2_db.commit()

    v2_db.close()

    print("=" * 60)
    if dry_run:
        print(f"DRY RUN — would insert {total_candidates - skipped_dup} challengers "
              f"({skipped_dup} already exist)")
    else:
        print(f"Done: inserted={inserted}, skipped_dup={skipped_dup}, "
              f"total_candidates={total_candidates}")
    print()
    print("Next steps:")
    print("  • Seeded challengers are staged as 'backtest'")
    print("  • They will be retrained on v2 features + path-dependent labels")
    print("  • The next 4h cycle (orchestration/run_cycle.py) will pick them up")
    print("  • Configs that pass v2 gates → promoted to forward_test arena")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("=== DRY RUN (no DB writes) ===\n")
    seed_challengers(dry_run=dry_run)
