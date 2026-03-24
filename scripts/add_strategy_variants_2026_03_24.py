#!/usr/bin/env python3
"""Add 7 new strategy variants to tournament backtest queue — 2026-03-24."""

import hashlib
import json
import sqlite3
import time
from pathlib import Path

# Strategy variant specs from strategy_ideas/2026-03-24-moonshot.md
VARIANTS = [
    {
        "name": "momentum_specialist_short",
        "direction": "short",
        "model_type": "xgboost",
        "params": {
            "n_estimators": 200,
            "learning_rate": 0.05,
            "max_depth": 6,
            "neg_class_weight": 5,
            "confidence_threshold": 0.50,
        },
        "features": [
            "momentum_4w", "momentum_8w", "volume_ratio_7d",
            "volume_spike", "obv_slope", "btc_30d_return"
        ],
    },
    {
        "name": "volatility_breakout_long",
        "direction": "long",
        "model_type": "lightgbm",
        "params": {
            "n_estimators": 200,
            "learning_rate": 0.01,
            "max_depth": 8,
            "num_leaves": 127,
            "neg_class_weight": 8,
            "confidence_threshold": 0.40,
        },
        "features": [
            "atr_compression", "bb_squeeze_pct", "high_low_range_pct",
            "volume_spike", "oi_change_24h"
        ],
    },
    {
        "name": "social_sentiment_boost_short",
        "direction": "short",
        "model_type": "catboost",
        "params": {
            "n_estimators": 200,
            "learning_rate": 0.05,
            "max_depth": 6,
            "neg_class_weight": 5,
            "confidence_threshold": 0.60,
        },
        "features": [
            # Core features
            "price_vs_52w_high", "price_vs_52w_low", "momentum_4w", "momentum_8w",
            "bb_squeeze_pct", "bb_position", "volume_ratio_7d", "volume_ratio_3d",
            "obv_slope", "volume_spike", "volume_trend", "atr_percentile",
            "atr_compression", "high_low_range_pct", "realized_vol_ratio",
            "distance_from_support", "distance_from_resistance", "consec_down_bars",
            "consec_up_bars", "higher_highs", "btc_30d_return", "btc_vol_percentile",
            "market_breadth", "days_since_listing", "is_new_listing",
            # Social features
            "fear_greed_score", "fear_greed_7d_change", "is_coingecko_trending",
            "trending_rank", "hours_on_trending", "news_mentions_24h",
            "news_mentions_7d_avg", "news_velocity_ratio", "reddit_mentions_24h",
            "reddit_score_24h", "reddit_velocity_ratio", "github_commits_7d",
            "github_commit_spike",
        ],
    },
    {
        "name": "high_confidence_filter_short",
        "direction": "short",
        "model_type": "xgboost",
        "params": {
            "n_estimators": 500,
            "learning_rate": 0.01,
            "max_depth": 10,
            "neg_class_weight": 3,
            "confidence_threshold": 0.80,
        },
        "features": "all",  # Will use all 50 features
    },
    {
        "name": "price_structure_expert_long",
        "direction": "long",
        "model_type": "lightgbm",
        "params": {
            "n_estimators": 100,
            "learning_rate": 0.1,
            "max_depth": 4,
            "num_leaves": 31,
            "neg_class_weight": 10,
            "confidence_threshold": 0.40,
        },
        "features": [
            "distance_from_support", "distance_from_resistance", "higher_highs",
            "consec_up_bars", "price_vs_52w_low", "volume_ratio_3d"
        ],
    },
    {
        "name": "oi_divergence_hunter_short",
        "direction": "short",
        "model_type": "catboost",
        "params": {
            "n_estimators": 200,
            "learning_rate": 0.05,
            "max_depth": 8,
            "neg_class_weight": 5,
            "confidence_threshold": 0.50,
        },
        "features": [
            "oi_price_divergence", "oi_change_7d", "oi_percentile_90d",
            "funding_rate_extreme", "price_vs_24h_high", "momentum_4w"
        ],
    },
    {
        "name": "regime_aware_ensemble_short",
        "direction": "short",
        "model_type": "xgboost",
        "params": {
            "n_estimators": 200,
            "learning_rate": 0.05,
            "max_depth": 6,
            "neg_class_weight": 5,
            "confidence_threshold": 0.60,
        },
        "features": [
            "btc_30d_return", "btc_vol_percentile", "market_breadth",
            "momentum_4w", "volume_ratio_7d", "atr_percentile"
        ],
    },
]


def generate_model_id(variant_spec):
    """Generate deterministic model_id from variant spec."""
    # Create stable hash from direction + params + features
    content = json.dumps({
        "direction": variant_spec["direction"],
        "model_type": variant_spec["model_type"],
        "params": variant_spec["params"],
        "features": variant_spec["features"],
        "timestamp": int(time.time()),
    }, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def insert_variant(db, variant_spec):
    """Insert variant into tournament_models table."""
    model_id = generate_model_id(variant_spec)
    
    params_json = json.dumps({
        "model_type": variant_spec["model_type"],
        **variant_spec["params"],
        "feature_list": variant_spec["features"],
    })
    
    # Determine feature_set string for DB
    if variant_spec["features"] == "all":
        feature_set = "all"
    elif isinstance(variant_spec["features"], list):
        feature_set = f"custom_{len(variant_spec['features'])}"
    else:
        feature_set = str(variant_spec["features"])
    
    db.execute("""
        INSERT INTO tournament_models (
            model_id, direction, stage, model_type, params,
            feature_set, feature_version, created_at
        ) VALUES (?, ?, 'backtest_pending', ?, ?, ?, 'v2_strategy', ?)
    """, (
        model_id,
        variant_spec["direction"],
        variant_spec["model_type"],
        params_json,
        feature_set,
        int(time.time()),
    ))
    
    return model_id


def main():
    db_path = Path(__file__).parent.parent / "data" / "moonshot_v2.db"
    db = sqlite3.connect(db_path)
    
    print("🎯 Adding 7 strategy variants to backtest queue...")
    print()
    
    created_ids = []
    for i, variant in enumerate(VARIANTS, 1):
        model_id = insert_variant(db, variant)
        created_ids.append(model_id)
        
        feature_count = len(variant["features"]) if isinstance(variant["features"], list) else "50 (all)"
        print(f"{i}. {variant['name']}")
        print(f"   ID: {model_id}")
        print(f"   Direction: {variant['direction']}")
        print(f"   Model: {variant['model_type']}")
        print(f"   Features: {feature_count}")
        print(f"   Threshold: {variant['params']['confidence_threshold']}")
        print()
    
    db.commit()
    db.close()
    
    print(f"✅ Added {len(created_ids)} models to backtest queue")
    print(f"📊 Next tournament cycle will process them")
    print()
    print("Model IDs:")
    for model_id in created_ids:
        print(f"  - {model_id}")


if __name__ == "__main__":
    main()
