#!/usr/bin/env python3
"""Insert 2026-03-28 Moonshot Scout variants into tournament queue.

These configs use simplified format (no entry/invalidation thresholds, no description).
"""

import json
import sqlite3
import time
import uuid
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "moonshot_v2.db"


def insert_variant(db, config_path):
    """Insert a single variant config into tournament_models table."""
    with open(config_path) as f:
        cfg = json.load(f)
    
    # Generate unique model_id
    model_id = uuid.uuid4().hex[:12]
    
    # Build params dict from config (excluding feature_set and direction)
    params = {k: v for k, v in cfg.items() if k not in ["feature_set", "direction"]}
    params["direction"] = cfg["direction"]
    params["feature_set"] = "no_social"  # All 2026-03-28 scouts use no_social
    
    # Serialize as JSON strings (DB schema stores as TEXT)
    params_json = json.dumps(params)
    feature_set_json = json.dumps(cfg["feature_set"])
    
    # Current timestamp
    created_at = int(time.time() * 1000)
    
    # Use default thresholds (will be optimized during backtest)
    entry_threshold = 0.5
    invalidation_threshold = 0.5
    
    # Insert into backtest queue
    db.execute(
        """
        INSERT INTO tournament_models 
        (model_id, direction, stage, model_type, params, feature_set, feature_version,
         entry_threshold, invalidation_threshold, created_at)
        VALUES (?, ?, 'seeded', ?, ?, ?, 'v2', ?, ?, ?)
        """,
        (
            model_id,
            cfg["direction"],
            cfg["model_type"],
            params_json,
            feature_set_json,
            entry_threshold,
            invalidation_threshold,
            created_at,
        )
    )
    
    return model_id, cfg


def main():
    """Load all 2026-03-28-scout configs and insert into tournament queue."""
    config_dir = Path(__file__).parent / "configs" / "generated"
    config_files = sorted(config_dir.glob("2026-03-28-scout-*.json"))
    
    if not config_files:
        print(f"❌ No 2026-03-28-scout-*.json files found in {config_dir}")
        return 1
    
    print(f"📥 Inserting {len(config_files)} scout variants into tournament queue...\n")
    
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    
    inserted = []
    
    for config_path in config_files:
        try:
            model_id, cfg = insert_variant(db, config_path)
            variant_name = config_path.stem.replace("2026-03-28-scout-", "")
            print(f"✅ {variant_name}")
            print(f"   Model ID: {model_id}")
            print(f"   {cfg['direction']:5s} | {cfg['model_type']:8s} | {len(cfg['feature_set'])} features")
            inserted.append((model_id, cfg, variant_name))
        except Exception as e:
            print(f"❌ Failed to insert {config_path.name}: {e}")
            import traceback
            traceback.print_exc()
            db.rollback()
            return 1
    
    # Commit all inserts
    db.commit()
    db.close()
    
    print(f"\n{'='*80}")
    print(f"✅ Successfully inserted {len(inserted)} scout variants!")
    print(f"\nModel IDs:")
    for model_id, cfg, variant_name in inserted:
        print(f"  {model_id}  {cfg['direction']:5s}  {cfg['model_type']:10s}  {variant_name}")
    
    print(f"\n🎯 Next tournament cycle will backtest these models (moonshot-v2.timer, 4h)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
