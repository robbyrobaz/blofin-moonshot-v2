#!/usr/bin/env python3
"""Insert Moonshot Strategy Scout variants into tournament_models."""

import hashlib
import json
import sqlite3
import sys
import time
from pathlib import Path

def make_model_id(params: dict) -> str:
    """Generate deterministic model ID from params."""
    blob = json.dumps(params, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()[:12]

def main():
    # Paths
    repo_root = Path(__file__).parent.parent.parent
    db_path = repo_root / "data" / "moonshot_v2.db"
    configs_dir = repo_root / "configs" / "generated"
    
    # Find all scout configs
    scout_configs = sorted(configs_dir.glob("2026-03-21-scout-*.json"))
    if not scout_configs:
        print("❌ No scout configs found")
        sys.exit(1)
    
    print(f"Found {len(scout_configs)} scout config files")
    
    # Connect to DB
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    
    now_ms = int(time.time() * 1000)
    inserted = 0
    skipped = 0
    
    for config_path in scout_configs:
        with open(config_path) as f:
            params = json.load(f)
        
        # Generate model_id
        model_id = make_model_id(params)
        direction = params["direction"]
        model_type = params["model_type"]
        entry_threshold = params["confidence_threshold"]
        feature_set = json.dumps(params["feature_set"])
        params_json = json.dumps(params, sort_keys=True)
        
        # Check if exists
        existing = db.execute(
            "SELECT model_id FROM tournament_models WHERE model_id = ?",
            (model_id,)
        ).fetchone()
        
        if existing:
            print(f"⏭️  SKIP {config_path.name} (model_id={model_id} exists)")
            skipped += 1
            continue
        
        # Insert
        db.execute(
            """INSERT INTO tournament_models
               (model_id, direction, stage, model_type, params, feature_set,
                entry_threshold, created_at)
               VALUES (?, ?, 'backtest', ?, ?, ?, ?, ?)""",
            (model_id, direction, model_type, params_json, feature_set,
             entry_threshold, now_ms)
        )
        print(f"✅ INSERT {config_path.name} → model_id={model_id} ({direction} {model_type})")
        inserted += 1
    
    db.commit()
    db.close()
    
    print(f"\n✅ Inserted {inserted} new variants, skipped {skipped}")
    print("Next tournament cycle will backtest these models.")

if __name__ == "__main__":
    main()
