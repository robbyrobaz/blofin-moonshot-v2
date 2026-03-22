#!/usr/bin/env python3
"""Insert 2026-03-22 scout variants into tournament_models table."""

import hashlib
import json
import sqlite3
import time
from pathlib import Path

DB_PATH = "/home/rob/.openclaw/workspace/blofin-moonshot-v2/data/moonshot_v2.db"
CONFIG_DIR = Path("/home/rob/.openclaw/workspace/blofin-moonshot-v2/configs/generated")

def generate_model_id(config):
    """Generate deterministic model_id from config."""
    canonical = json.dumps(config, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]

def insert_model(db, config_path):
    """Insert a single model config into the database."""
    with open(config_path) as f:
        config = json.load(f)
    
    model_id = generate_model_id(config)
    direction = config.get("direction", "short")
    model_type = config.get("model_type", "xgboost")
    
    # Build params dict (everything except direction and feature_set)
    params = {k: v for k, v in config.items() if k not in ("direction", "feature_set")}
    params_json = json.dumps(params)
    
    feature_set_json = json.dumps(config.get("feature_set", []))
    
    now_ms = int(time.time() * 1000)
    
    try:
        db.execute(
            """
            INSERT INTO tournament_models (
                model_id, direction, stage, model_type, params, feature_set,
                created_at, bt_trades, bt_pf, bt_precision, bt_pnl,
                ft_trades, ft_wins, ft_pnl, ft_pf
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0.0, 0.0, 0.0, 0, 0, 0.0, 0.0)
            """,
            (model_id, direction, "backtest_queue", model_type, params_json, 
             feature_set_json, now_ms)
        )
        db.commit()
        print(f"✓ Inserted {model_id} ({direction}, {model_type}) from {config_path.name}")
        return model_id
    except sqlite3.IntegrityError:
        print(f"✗ Skipped {model_id} (already exists) from {config_path.name}")
        return None

def main():
    db = sqlite3.connect(DB_PATH)
    
    # Find all 2026-03-22-scout-*.json files
    config_files = sorted(CONFIG_DIR.glob("2026-03-22-scout-*.json"))
    
    if not config_files:
        print("No config files found matching 2026-03-22-scout-*.json")
        return
    
    print(f"Found {len(config_files)} config files to insert\n")
    
    inserted = []
    for config_file in config_files:
        model_id = insert_model(db, config_file)
        if model_id:
            inserted.append(model_id)
    
    # Check queue size
    queue_size = db.execute(
        "SELECT COUNT(*) FROM tournament_models WHERE stage = 'backtest_queue'"
    ).fetchone()[0]
    
    print(f"\n✓ Inserted {len(inserted)} new models")
    print(f"✓ Backtest queue size: {queue_size}")
    print(f"\nModel IDs created:")
    for mid in inserted:
        print(f"  - {mid}")
    
    db.close()

if __name__ == "__main__":
    main()
